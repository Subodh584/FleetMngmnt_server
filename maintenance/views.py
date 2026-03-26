from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsMaintenanceStaffOrFleetManager
from .models import MaintenanceSchedule, MaintenanceRecord, SparePart, SparePartUsed
from .serializers import (
    MaintenanceScheduleSerializer,
    MaintenanceRecordSerializer,
    MaintenanceRecordCreateSerializer,
    SparePartSerializer,
    SparePartUsedSerializer,
)


class MaintenanceScheduleViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceSchedule.objects.select_related('vehicle', 'scheduled_by').all()
    serializer_class = MaintenanceScheduleSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['vehicle', 'maintenance_type', 'status', 'scheduled_date']
    ordering_fields = ['scheduled_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(scheduled_by=self.request.user)


class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRecord.objects.select_related(
        'vehicle', 'schedule', 'issue', 'assigned_to', 'assigned_by',
    ).prefetch_related('spare_parts').all()
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['vehicle', 'maintenance_type', 'repair_status', 'assigned_to']
    ordering_fields = ['created_at', 'started_at', 'completed_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return MaintenanceRecordCreateSerializer
        return MaintenanceRecordSerializer

    @action(detail=True, methods=['post'])
    def start_repair(self, request, pk=None):
        record = self.get_object()
        if record.repair_status != 'pending':
            return Response(
                {'detail': 'Can only start from pending status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record.repair_status = 'in_progress'
        record.started_at = timezone.now()
        record.save()
        return Response(MaintenanceRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def complete_repair(self, request, pk=None):
        record = self.get_object()
        if record.repair_status != 'in_progress':
            return Response(
                {'detail': 'Can only complete from in_progress status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record.repair_status = 'completed'
        record.completed_at = timezone.now()
        record.total_cost = request.data.get('total_cost', record.total_cost)
        record.technician_notes = request.data.get('technician_notes', record.technician_notes)
        if 'parts_used' in request.data:
            record.parts_used = request.data['parts_used']
        record.save()
        # Set vehicle back to available
        vehicle = record.vehicle
        vehicle.status = 'available'
        vehicle.last_service_date = timezone.now().date()
        if record.mileage_at_service:
            vehicle.current_mileage_km = record.mileage_at_service
        vehicle.save(update_fields=['status', 'last_service_date', 'current_mileage_km', 'updated_at'])
        # Also update schedule if linked
        if record.schedule:
            record.schedule.status = 'completed'
            record.schedule.save(update_fields=['status', 'updated_at'])
        # Also update issue if linked
        if record.issue:
            record.issue.status = 'resolved'
            record.issue.save(update_fields=['status', 'updated_at'])
        return Response(MaintenanceRecordSerializer(record).data)


class SparePartViewSet(viewsets.ModelViewSet):
    serializer_class = SparePartSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['maintenance']

    def get_queryset(self):
        return SparePart.objects.select_related('maintenance').all()


class SparePartUsedViewSet(viewsets.ModelViewSet):
    serializer_class = SparePartUsedSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['maintenance']

    def get_queryset(self):
        return SparePartUsed.objects.select_related('maintenance').all()
