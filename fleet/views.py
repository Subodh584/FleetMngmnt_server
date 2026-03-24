from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import (
    Vehicle, InspectionChecklist, InspectionChecklistItem,
    Inspection, InspectionResult, VehicleIssue,
)
from .serializers import (
    VehicleSerializer, InspectionChecklistSerializer,
    InspectionChecklistItemSerializer, InspectionSerializer,
    InspectionCreateSerializer, InspectionResultSerializer,
    VehicleIssueSerializer, VehicleIssueDetailSerializer,
)
from core.permissions import (
    IsFleetManager, IsFleetManagerOrReadOnly, IsMaintenanceStaffOrFleetManager,
)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsFleetManagerOrReadOnly]
    filterset_fields = ['status', 'fuel_type', 'make']
    search_fields = ['registration_no', 'make', 'model', 'vin']
    ordering_fields = ['created_at', 'current_mileage_km', 'registration_no']

    @action(detail=True, methods=['get'])
    def inspections(self, request, pk=None):
        vehicle = self.get_object()
        inspections = vehicle.inspections.all().order_by('-submitted_at')
        page = self.paginate_queryset(inspections)
        serializer = InspectionSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def issues(self, request, pk=None):
        vehicle = self.get_object()
        issues = vehicle.issues.all().order_by('-reported_at')
        page = self.paginate_queryset(issues)
        serializer = VehicleIssueSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class InspectionChecklistViewSet(viewsets.ModelViewSet):
    queryset = InspectionChecklist.objects.prefetch_related('items').all()
    serializer_class = InspectionChecklistSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['is_active']
    search_fields = ['name']

    @action(
        detail=False,
        methods=['get'],
        url_path='pre_trip_default',
        permission_classes=[permissions.IsAuthenticated],
    )
    def pre_trip_default(self, request):
        """Return the active default Pre-Trip Inspection checklist with items."""
        checklist = (
            InspectionChecklist.objects.prefetch_related('items')
            .filter(name='Pre-Trip Inspection', is_active=True)
            .first()
        )
        if checklist is None:
            return Response(
                {'detail': 'No active pre-trip checklist found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InspectionChecklistSerializer(checklist).data)


class InspectionChecklistItemViewSet(viewsets.ModelViewSet):
    queryset = InspectionChecklistItem.objects.all()
    serializer_class = InspectionChecklistItemSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['checklist']


class InspectionViewSet(viewsets.ModelViewSet):
    queryset = Inspection.objects.select_related(
        'vehicle', 'driver', 'checklist', 'reviewed_by', 'assigned_to_manager',
    ).prefetch_related('results').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['vehicle', 'driver', 'inspection_type', 'overall_status', 'assigned_to_manager']
    ordering_fields = ['submitted_at', 'created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return InspectionCreateSerializer
        return InspectionSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsMaintenanceStaffOrFleetManager])
    def review(self, request, pk=None):
        """Maintenance staff / fleet manager reviews an inspection."""
        inspection = self.get_object()
        new_status = request.data.get('overall_status')
        if new_status not in ('approved', 'flagged'):
            return Response(
                {'detail': 'status must be approved or flagged.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inspection.overall_status = new_status
        inspection.reviewed_by = request.user
        inspection.reviewed_at = timezone.now()
        inspection.save()
        return Response(InspectionSerializer(inspection).data)

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def approve(self, request, pk=None):
        """Fleet manager approves a flagged inspection."""
        inspection = self.get_object()
        inspection.approved = True
        inspection.save(update_fields=['approved'])
        return Response(InspectionSerializer(inspection).data)


class VehicleIssueViewSet(viewsets.ModelViewSet):
    queryset = VehicleIssue.objects.select_related(
        'vehicle',
        'reported_by', 'reported_by__profile',
        'inspection', 'inspection__checklist',
        'assigned_to_manager', 'assigned_to_manager__profile',
    ).prefetch_related(
        'inspection__results__checklist_item',
    ).all()
    serializer_class = VehicleIssueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['vehicle', 'reported_by', 'severity', 'status', 'assigned_to_manager']
    search_fields = ['title', 'description']
    ordering_fields = ['reported_at', 'severity']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleIssueDetailSerializer
        return VehicleIssueSerializer

    def perform_create(self, serializer):
        inspection = serializer.validated_data.get('inspection')
        assigned_manager = None
        if inspection:
            # Prefer the manager already stamped on the inspection record
            if inspection.assigned_to_manager_id:
                assigned_manager = inspection.assigned_to_manager
            elif inspection.trip_id and inspection.trip.assigned_by_id:
                assigned_manager = inspection.trip.assigned_by
        serializer.save(reported_by=self.request.user, assigned_to_manager=assigned_manager)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_status = serializer.validated_data.get('status', instance.status)

        # Auto-assign the current fleet manager when they are the first to acknowledge.
        if (
            new_status == 'acknowledged'
            and instance.status == 'reported'
            and instance.assigned_to_manager is None
        ):
            serializer.save(assigned_to_manager=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def approve(self, request, pk=None):
        """Fleet manager approves a vehicle issue."""
        issue = self.get_object()
        issue.approved = True
        issue.save(update_fields=['approved'])
        return Response(VehicleIssueSerializer(issue).data)
