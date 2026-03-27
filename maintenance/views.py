import calendar

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
    """
    Endpoints for proactive planning of physical fleet services.
    Flags physical assets as locked before actual downtime begins.
    """
    queryset = MaintenanceSchedule.objects.select_related('vehicle', 'scheduled_by').all()
    serializer_class = MaintenanceScheduleSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['vehicle', 'maintenance_type', 'status', 'scheduled_date']
    ordering_fields = ['scheduled_date', 'created_at']

    def perform_create(self, serializer):
        """Implicitly links schedule ownership and blocks dispatchable vehicle status instantly."""
        schedule = serializer.save(scheduled_by=self.request.user)
        vehicle = schedule.vehicle
        vehicle.status = 'under_maintenance'
        vehicle.save(update_fields=['status', 'updated_at'])


class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    """
    Tracks the active or historical repair states occurring in the physical shop.
    Automatically coordinates complex resolution hooks back up to Fleet Vehicles and user Issue reports.
    """
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
        """Acknowledge active wrench-time physically beginning on the asset."""
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
        """
        Extremely crucial lifecycle hook concluding a repair.
        Recalculates subsequent compliance due dates and frees vehicles dynamically back to 'available'.
        Hooks into associated structural bugs (`VehicleIssue`) to cascade resolutions cleanly.
        """
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
        record.save()
        
        # Set vehicle back to available and reset service tracking logic safely
        vehicle = record.vehicle
        vehicle.status = 'available'
        vehicle.last_service_date = timezone.now().date()
        
        today = timezone.now().date()
        # Naive 4 month forward compliance skip
        month = today.month + 4
        year = today.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(today.day, calendar.monthrange(year, month)[1])
        vehicle.next_service_due_date = today.replace(year=year, month=month, day=day)
        
        if record.mileage_at_service:
            vehicle.current_mileage_km = record.mileage_at_service
        vehicle.save(update_fields=['status', 'last_service_date', 'next_service_due_date', 'current_mileage_km', 'updated_at'])
        
        # Retroactively close out governing scheduled containers
        if record.schedule:
            record.schedule.status = 'completed'
            record.schedule.save(update_fields=['status', 'updated_at'])
            
        # Retroactively clear originating driver fault logs 
        if record.issue:
            record.issue.status = 'resolved'
            record.issue.save(update_fields=['status', 'updated_at'])
            
        return Response(MaintenanceRecordSerializer(record).data)


class SparePartViewSet(viewsets.ModelViewSet):
    """Loose inventory tracking endpoint."""
    serializer_class = SparePartSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['maintenance']

    def get_queryset(self):
        return SparePart.objects.select_related('maintenance').all()


class SparePartUsedViewSet(viewsets.ModelViewSet):
    """Query ledger detailing strictly consumed components on resolved repairs."""
    serializer_class = SparePartUsedSerializer
    permission_classes = [IsMaintenanceStaffOrFleetManager]
    filterset_fields = ['maintenance']

    def get_queryset(self):
        return SparePartUsed.objects.select_related('maintenance').all()
