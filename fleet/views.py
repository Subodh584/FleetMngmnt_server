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
    VehicleIssueSerializer,
)
from core.permissions import (
    IsFleetManagerOrReadOnly, IsMaintenanceStaffOrFleetManager,
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


class InspectionChecklistItemViewSet(viewsets.ModelViewSet):
    queryset = InspectionChecklistItem.objects.all()
    serializer_class = InspectionChecklistItemSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['checklist']


class InspectionViewSet(viewsets.ModelViewSet):
    queryset = Inspection.objects.select_related(
        'vehicle', 'driver', 'checklist', 'reviewed_by',
    ).prefetch_related('results').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['vehicle', 'driver', 'inspection_type', 'overall_status']
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


class VehicleIssueViewSet(viewsets.ModelViewSet):
    queryset = VehicleIssue.objects.select_related('vehicle', 'reported_by').all()
    serializer_class = VehicleIssueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['vehicle', 'reported_by', 'severity', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['reported_at', 'severity']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)
