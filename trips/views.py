from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsDriver, IsFleetManager, IsFleetManagerOrReadOnly
from fleet.models import Inspection
from .models import (
    Order, OrderDropPoint, Trip, Route, RouteDeviation,
    GpsLog, GeofenceEvent, TripExpense, FuelLog, DeliveryProof,
    DriverLocation, OdometerImage,
)
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderDropPointSerializer,
    BulkDropPointSerializer,
    TripSerializer, TripCreateSerializer, RouteSerializer,
    RouteDeviationSerializer, GpsLogSerializer, GeofenceEventSerializer,
    TripExpenseSerializer, FuelLogSerializer, DeliveryProofSerializer,
    DriverLocationSerializer, DriverLocationUpdateSerializer,
    OdometerImageSerializer,
)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('created_by', 'warehouse').prefetch_related('drop_points').all()
    permission_classes = [IsFleetManagerOrReadOnly]
    filterset_fields = ['status', 'warehouse', 'created_by']
    search_fields = ['order_ref', 'notes']
    ordering_fields = ['created_at', 'status']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @action(detail=True, methods=['patch'], url_path='drop_points', url_name='set_drop_points')
    def set_drop_points(self, request, pk=None):
        """
        Replace all drop points for an order in one call.
        Accepts { "drop_points": [ { location_id, sequence_no, ... }, ... ] }
        """
        order = self.get_object()
        serializer = BulkDropPointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_drop_points = serializer.validated_data['drop_points']

        # Delete existing and recreate atomically
        from django.db import transaction
        with transaction.atomic():
            order.drop_points.all().delete()
            OrderDropPoint.objects.bulk_create([
                OrderDropPoint(
                    order=order,
                    location_id=dp['location_id'],
                    sequence_no=dp['sequence_no'],
                    contact_name=dp.get('contact_name', ''),
                    contact_phone=dp.get('contact_phone', ''),
                    notes=dp.get('notes', ''),
                )
                for dp in new_drop_points
            ])

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)


class OrderDropPointViewSet(viewsets.ModelViewSet):
    queryset = OrderDropPoint.objects.select_related('order', 'location').all()
    serializer_class = OrderDropPointSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['order', 'status']

    def perform_update(self, serializer):
        """Auto-set arrived_at / delivered_at timestamps on status transitions."""
        new_status = serializer.validated_data.get('status')
        instance = serializer.instance
        now = timezone.now()

        extra = {}
        if new_status == 'arrived' and instance.status != 'arrived':
            extra['arrived_at'] = now
        elif new_status == 'delivered' and instance.status != 'delivered':
            extra['delivered_at'] = now

        serializer.save(**extra)


# ---------------------------------------------------------------------------
# Trips
# ---------------------------------------------------------------------------

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.select_related(
        'order', 'order__warehouse', 'vehicle', 'driver', 'assigned_by', 'route_detail',
    ).prefetch_related(
        'order__drop_points', 'order__drop_points__location',
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'driver', 'vehicle', 'order']
    search_fields = ['order__order_ref']
    ordering_fields = ['created_at', 'started_at', 'scheduled_start']

    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        return TripSerializer

    # -- Custom actions -------------------------------------------------------

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Driver starts a trip."""
        trip = self.get_object()
        if trip.status not in ('assigned', 'accepted'):
            return Response(
                {'detail': 'Trip can only be started from assigned or accepted status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        trip.status = 'in_progress'
        trip.started_at = timezone.now()
        trip.start_location_lat = request.data.get('latitude')
        trip.start_location_lng = request.data.get('longitude')
        trip.start_mileage_km = request.data.get('start_mileage_km', trip.start_mileage_km)
        trip.save()
        # Link pre-trip inspection to this trip if provided
        inspection_id = request.data.get('inspection_id')
        if inspection_id is not None:
            try:
                insp = Inspection.objects.get(pk=inspection_id, driver=request.user)
                insp.trip = trip
                insp.save(update_fields=['trip'])
            except Inspection.DoesNotExist:
                pass  # invalid or unauthorized inspection_id — don't block trip start
        # Update vehicle status
        trip.vehicle.status = 'in_trip'
        trip.vehicle.save(update_fields=['status', 'updated_at'])
        # Update order status
        trip.order.status = 'in_transit'
        trip.order.save(update_fields=['status', 'updated_at'])
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Driver completes a trip."""
        trip = self.get_object()
        if trip.status != 'in_progress':
            return Response(
                {'detail': 'Trip can only be completed from in_progress status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        trip.status = 'completed'
        trip.ended_at = timezone.now()
        trip.end_location_lat = request.data.get('latitude')
        trip.end_location_lng = request.data.get('longitude')
        trip.end_mileage_km = request.data.get('end_mileage_km', trip.end_mileage_km)
        trip.save()
        # Update vehicle
        vehicle = trip.vehicle
        vehicle.status = 'available'
        if trip.end_mileage_km:
            vehicle.current_mileage_km = trip.end_mileage_km
        vehicle.save(update_fields=['status', 'current_mileage_km', 'updated_at'])
        # Check if all order trips are complete
        order = trip.order
        if not order.trips.exclude(status='completed').exists():
            order.status = 'delivered'
            order.save(update_fields=['status', 'updated_at'])
        # Set driver to on_rest for 9 hours
        profile = trip.driver.profile
        rest_ends = trip.ended_at + timezone.timedelta(hours=9)
        profile.driver_status = 'on_rest'
        profile.rest_ends_at = rest_ends
        profile.save(update_fields=['driver_status', 'rest_ends_at', 'updated_at'])
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a trip."""
        trip = self.get_object()
        if trip.status in ('completed', 'cancelled'):
            return Response(
                {'detail': 'Cannot cancel a completed or already cancelled trip.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        trip.status = 'cancelled'
        trip.save()
        trip.vehicle.status = 'available'
        trip.vehicle.save(update_fields=['status', 'updated_at'])
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Driver accepts an assigned trip — transitions directly to in_progress."""
        trip = self.get_object()
        if trip.status != 'assigned':
            return Response(
                {'detail': 'Trip can only be accepted from assigned status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if trip.driver_id != request.user.id:
            return Response({'detail': 'You are not the driver for this trip.'}, status=status.HTTP_403_FORBIDDEN)
        trip.status = 'accepted'
        trip.save(update_fields=['status', 'updated_at'])
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Driver rejects an assigned trip — reverts to pending and notifies fleet managers."""
        trip = self.get_object()
        if trip.status != 'assigned':
            return Response(
                {'detail': 'Trip can only be rejected from assigned status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if trip.driver_id != request.user.id:
            return Response({'detail': 'You are not the driver for this trip.'}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get('reason', '')
        trip.status = 'rejected'
        trip.rejection_reason = reason
        trip.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        # Free the vehicle
        trip.vehicle.status = 'available'
        trip.vehicle.save(update_fields=['status', 'updated_at'])
        # Reset order back to pending so fleet manager can reassign
        trip.order.status = 'pending'
        trip.order.save(update_fields=['status', 'updated_at'])
        # Notify all fleet managers
        from comms.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        driver_name = request.user.get_full_name() or request.user.username
        managers = User.objects.filter(profile__role='fleet_manager')
        Notification.objects.bulk_create([
            Notification(
                user=mgr,
                alert_type='trip_rejected',
                title='Trip Rejected',
                body=f'Driver {driver_name} rejected Trip #{trip.id} (Order {trip.order.order_ref}). Reason: {reason or "No reason given."}',
                reference_id=trip.pk,
                reference_type='trip',
            )
            for mgr in managers
        ])
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        """Get the latest GPS position for a trip."""
        trip = self.get_object()
        latest = trip.gps_logs.order_by('-recorded_at').first()
        if not latest:
            return Response({'detail': 'No GPS data available.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(GpsLogSerializer(latest).data)

    @action(detail=True, methods=['get'])
    def gps_history(self, request, pk=None):
        """Get the full GPS trail for a trip."""
        trip = self.get_object()
        logs = trip.gps_logs.order_by('recorded_at')
        page = self.paginate_queryset(logs)
        serializer = GpsLogSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def expenses(self, request, pk=None):
        trip = self.get_object()
        exps = trip.expenses.all()
        page = self.paginate_queryset(exps)
        return self.get_paginated_response(TripExpenseSerializer(page, many=True).data)

    @action(detail=True, methods=['get'])
    def fuel(self, request, pk=None):
        trip = self.get_object()
        logs = trip.fuel_logs.all()
        page = self.paginate_queryset(logs)
        return self.get_paginated_response(FuelLogSerializer(page, many=True).data)

    @action(detail=True, methods=['get'])
    def odometer_images(self, request, pk=None):
        """Get all odometer images for a trip."""
        trip = self.get_object()
        images = trip.odometer_images.all().order_by('recorded_at')
        page = self.paginate_queryset(images)
        return self.get_paginated_response(OdometerImageSerializer(page, many=True).data)


# ---------------------------------------------------------------------------
# Driver locations
# ---------------------------------------------------------------------------

class DriverLocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Current driver locations. Drivers upsert via the `update_location` action;
    fleet managers can list / retrieve via standard GET.
    """
    queryset = DriverLocation.objects.select_related('trip', 'driver', 'vehicle').all()
    serializer_class = DriverLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'driver', 'vehicle']

    @action(detail=False, methods=['post'], permission_classes=[IsDriver])
    def update_location(self, request):
        """
        Driver calls this endpoint to store / update their current location.
        Creates a new DriverLocation row on first call for a trip+driver;
        updates the existing row on subsequent calls.
        Also broadcasts the update to the WebSocket room for live tracking.
        """
        serializer = DriverLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate trip belongs to this driver and is in progress
        try:
            trip = Trip.objects.select_related('vehicle').get(id=data['trip_id'])
        except Trip.DoesNotExist:
            return Response(
                {'detail': 'Trip not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if trip.driver_id != request.user.id:
            return Response(
                {'detail': 'You are not the driver for this trip.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if trip.status not in ('in_progress', 'assigned'):
            return Response(
                {'detail': 'Trip is not active (must be assigned or in_progress).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Upsert: create on first call, update on subsequent calls
        location, created = DriverLocation.objects.update_or_create(
            trip=trip,
            driver=request.user,
            defaults={
                'vehicle': trip.vehicle,
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'speed_kmh': data.get('speed_kmh'),
                'heading_deg': data.get('heading_deg'),
            },
        )

        # Broadcast to WebSocket room so fleet managers see live updates
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'trip_{trip.id}_tracking',
            {
                'type': 'gps_update',
                'data': {
                    'trip_id': trip.id,
                    'driver_id': request.user.id,
                    'latitude': float(data['latitude']),
                    'longitude': float(data['longitude']),
                    'speed_kmh': float(data['speed_kmh']) if data.get('speed_kmh') else None,
                    'heading_deg': float(data['heading_deg']) if data.get('heading_deg') else None,
                    'updated_at': str(location.updated_at),
                },
            },
        )

        return Response(
            DriverLocationSerializer(location).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related('trip', 'approved_by').all()
    serializer_class = RouteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip']

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def approve(self, request, pk=None):
        route = self.get_object()
        route.approved_by = request.user
        route.approved_at = timezone.now()
        route.save()
        return Response(RouteSerializer(route).data)


# ---------------------------------------------------------------------------
# Route deviations
# ---------------------------------------------------------------------------

class RouteDeviationViewSet(viewsets.ModelViewSet):
    queryset = RouteDeviation.objects.all()
    serializer_class = RouteDeviationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip']


# ---------------------------------------------------------------------------
# GPS logs
# ---------------------------------------------------------------------------

class GpsLogViewSet(viewsets.ModelViewSet):
    queryset = GpsLog.objects.select_related('trip', 'vehicle').all()
    serializer_class = GpsLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'vehicle']
    ordering_fields = ['recorded_at']


# ---------------------------------------------------------------------------
# Geofence events
# ---------------------------------------------------------------------------

class GeofenceEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeofenceEvent.objects.select_related(
        'trip', 'vehicle', 'geofence', 'drop_point',
    ).all()
    serializer_class = GeofenceEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'vehicle', 'geofence', 'event_type']


# ---------------------------------------------------------------------------
# Trip expenses
# ---------------------------------------------------------------------------

class TripExpenseViewSet(viewsets.ModelViewSet):
    queryset = TripExpense.objects.select_related('trip', 'driver').all()
    serializer_class = TripExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'driver', 'expense_type']

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)


# ---------------------------------------------------------------------------
# Fuel logs
# ---------------------------------------------------------------------------

class FuelLogViewSet(viewsets.ModelViewSet):
    queryset = FuelLog.objects.select_related('trip', 'vehicle', 'driver').all()
    serializer_class = FuelLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'vehicle', 'driver']

    def perform_create(self, serializer):
        trip = serializer.validated_data.get('trip')
        vehicle = trip.vehicle if trip else None
        serializer.save(driver=self.request.user, vehicle=vehicle)


# ---------------------------------------------------------------------------
# Odometer images
# ---------------------------------------------------------------------------

class OdometerImageViewSet(viewsets.ModelViewSet):
    queryset = OdometerImage.objects.select_related('trip', 'vehicle', 'driver').all()
    serializer_class = OdometerImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'vehicle', 'driver']

    def perform_create(self, serializer):
        trip = serializer.validated_data.get('trip')
        vehicle = trip.vehicle if trip else None
        serializer.save(driver=self.request.user, vehicle=vehicle)


# ---------------------------------------------------------------------------
# Delivery proofs
# ---------------------------------------------------------------------------

class DeliveryProofViewSet(viewsets.ModelViewSet):
    queryset = DeliveryProof.objects.select_related(
        'drop_point', 'trip', 'driver', 'verified_by',
    ).all()
    serializer_class = DeliveryProofSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'drop_point', 'proof_type']

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def verify(self, request, pk=None):
        """Fleet manager verifies a delivery proof."""
        proof = self.get_object()
        proof.verified_by = request.user
        proof.verified_at = timezone.now()
        proof.save()
        # Mark drop point as delivered
        drop_point = proof.drop_point
        if drop_point.status != 'delivered':
            drop_point.status = 'delivered'
            drop_point.delivered_at = timezone.now()
            drop_point.save()
        return Response(DeliveryProofSerializer(proof).data)
