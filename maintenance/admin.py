from django.contrib import admin

from .models import MaintenanceSchedule, MaintenanceRecord, SparePartUsed


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    """Admin configuration mapped to upcoming planned service routines."""
    list_display = ['id', 'vehicle', 'scheduled_by', 'maintenance_type', 'scheduled_date', 'status']
    list_filter = ['maintenance_type', 'status']
    raw_id_fields = ['vehicle', 'scheduled_by']


class SparePartUsedInline(admin.TabularInline):
    """Dynamic form integration placing explicit material consumption directly into active repair instances."""
    model = SparePartUsed
    extra = 0


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    """
    Central Fleet Manager workbench to observe real-time mechanic statuses seamlessly.
    """
    list_display = [
        'id', 'vehicle', 'maintenance_type', 'repair_status',
        'assigned_to', 'total_cost', 'started_at', 'completed_at',
    ]
    list_filter = ['maintenance_type', 'repair_status']
    raw_id_fields = ['vehicle', 'schedule', 'issue', 'assigned_to', 'assigned_by']
    inlines = [SparePartUsedInline]


@admin.register(SparePartUsed)
class SparePartUsedAdmin(admin.ModelAdmin):
    """Raw inventory ledger showing historical item allocations explicitly."""
    list_display = ['part_name', 'part_number', 'quantity', 'unit_cost', 'total_cost', 'maintenance']
    search_fields = ['part_name', 'part_number']
    raw_id_fields = ['maintenance']
