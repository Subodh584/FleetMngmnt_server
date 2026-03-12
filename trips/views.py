from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsFleetManager, IsFleetManagerOrReadOnly
from .models import (
    Order, OrderDropPoint, Trip, Route, RouteDeviation,
    GpsLog, GeofenceEvent, TripExpense, FuelLog, DeliveryProof,
)
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderDropPointSerializer,
    BulkDropPointSerializer,
    TripSerializer, TripCreateSerializer, RouteSerializer,
    RouteDeviationSerializer, GpsLogSerializer, GeofenceEventSerializer,
    TripExpenseSerializer, FuelLogSerializer, DeliveryProofSerializer,
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
        if trip.status != 'assigned':
            return Response(
                {'detail': 'Trip can only be started from assigned status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        trip.status = 'in_progress'
        trip.started_at = timezone.now()
        trip.start_location_lat = request.data.get('latitude')
        trip.start_location_lng = request.data.get('longitude')
        trip.start_mileage_km = request.data.get('start_mileage_km', trip.start_mileage_km)
        trip.save()
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
