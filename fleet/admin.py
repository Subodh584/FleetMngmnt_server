from django.contrib import admin

from .models import (
    Vehicle, InspectionChecklist, InspectionChecklistItem,
    Inspection, InspectionResult, VehicleIssue,
)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """
    Admin configuration for the core Vehicle model.
    Highlights current stats (fuel, mileage, status, registration).
    """
    list_display = ['registration_no', 'make', 'model', 'year', 'status', 'current_mileage_km', 'fuel_type']
    list_filter = ['status', 'fuel_type', 'make']
    search_fields = ['registration_no', 'make', 'model', 'vin']


class InspectionChecklistItemInline(admin.TabularInline):
    """Allows rapid addition/editing of Checklist Items directly inside the parent Checklist."""
    model = InspectionChecklistItem
    extra = 1


@admin.register(InspectionChecklist)
class InspectionChecklistAdmin(admin.ModelAdmin):
    """Admin configuration for standardizing check guidelines."""
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    inlines = [InspectionChecklistItemInline]


class InspectionResultInline(admin.TabularInline):
    """Lists each evaluated line-item requirement under an Inspection submission."""
    model = InspectionResult
    extra = 0


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    """
    Admin configuration for analyzing raw recorded Inspections.
    Uses 'raw_id_fields' to prevent timeout crashes when loading extensive trip databases.
    """
    list_display = ['id', 'vehicle', 'driver', 'inspection_type', 'overall_status', 'submitted_at']
    list_filter = ['inspection_type', 'overall_status']
    raw_id_fields = ['trip', 'vehicle', 'driver', 'checklist', 'reviewed_by']
    inlines = [InspectionResultInline]


@admin.register(VehicleIssue)
class VehicleIssueAdmin(admin.ModelAdmin):
    """
    Admin configuration for reported flaws and damages (VehicleIssue).
    Provides rapid assessment of issue urgencies.
    """
    list_display = ['title', 'vehicle', 'reported_by', 'severity', 'status', 'reported_at']
    list_filter = ['severity', 'status']
    search_fields = ['title', 'description']
    raw_id_fields = ['vehicle', 'reported_by', 'inspection']
