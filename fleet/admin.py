from django.contrib import admin

from .models import (
    Vehicle, InspectionChecklist, InspectionChecklistItem,
    Inspection, InspectionResult, VehicleIssue,
)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['registration_no', 'make', 'model', 'year', 'status', 'current_mileage_km', 'fuel_type']
    list_filter = ['status', 'fuel_type', 'make']
    search_fields = ['registration_no', 'make', 'model', 'vin']


class InspectionChecklistItemInline(admin.TabularInline):
    model = InspectionChecklistItem
    extra = 1


@admin.register(InspectionChecklist)
class InspectionChecklistAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    inlines = [InspectionChecklistItemInline]


class InspectionResultInline(admin.TabularInline):
    model = InspectionResult
    extra = 0


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'vehicle', 'driver', 'inspection_type', 'overall_status', 'submitted_at']
    list_filter = ['inspection_type', 'overall_status']
    raw_id_fields = ['trip', 'vehicle', 'driver', 'checklist', 'reviewed_by']
    inlines = [InspectionResultInline]


@admin.register(VehicleIssue)
class VehicleIssueAdmin(admin.ModelAdmin):
    list_display = ['title', 'vehicle', 'reported_by', 'severity', 'status', 'reported_at']
    list_filter = ['severity', 'status']
    search_fields = ['title', 'description']
    raw_id_fields = ['vehicle', 'reported_by', 'inspection']
