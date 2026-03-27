from django.contrib import admin

from .models import (
    Order, OrderDropPoint, Trip, Route, RouteDeviation,
    GpsLog, GeofenceEvent, TripExpense, FuelLog, DeliveryProof,
)


class OrderDropPointInline(admin.TabularInline):
    """Nests drop points natively natively inside Order dashboards for fluid updates."""
    model = OrderDropPoint
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Dashboard view rendering the high-level parent constraints for active consignments."""
    list_display = ['order_ref', 'created_by', 'warehouse', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['order_ref', 'notes']
    raw_id_fields = ['created_by', 'warehouse']
    inlines = [OrderDropPointInline]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    """
    Comprehensive readout of active operation schedules binding
    Drivers, assets (Vehicles), and requirements (Orders).
    """
    list_display = ['id', 'order', 'vehicle', 'driver', 'status', 'started_at', 'ended_at']
    list_filter = ['status']
    search_fields = ['order__order_ref']
    raw_id_fields = ['order', 'vehicle', 'driver', 'assigned_by']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    """Visualization hook for assessing pre-dispatch navigational instructions."""
    list_display = ['id', 'trip', 'total_distance_km', 'estimated_duration_min', 'approved_by']
    raw_id_fields = ['trip', 'approved_by']


@admin.register(RouteDeviation)
class RouteDeviationAdmin(admin.ModelAdmin):
    """Analyzes security breaches where tracked locations fell outside acceptable bounds."""
    list_display = ['id', 'trip', 'deviation_meters', 'detected_at', 'resolved_at']
    raw_id_fields = ['trip']


@admin.register(GpsLog)
class GpsLogAdmin(admin.ModelAdmin):
    """Supervisory lookup tool handling extremely dense, granular telemetry tables."""
    list_display = ['id', 'trip', 'vehicle', 'latitude', 'longitude', 'speed_kmh', 'recorded_at']
    list_filter = ['vehicle']
    raw_id_fields = ['trip', 'vehicle']


@admin.register(GeofenceEvent)
class GeofenceEventAdmin(admin.ModelAdmin):
    """Tracks raw physical state intersections with bounding boxes for audits."""
    list_display = ['id', 'trip', 'vehicle', 'geofence', 'event_type', 'occurred_at']
    list_filter = ['event_type']
    raw_id_fields = ['trip', 'vehicle', 'geofence', 'drop_point']


@admin.register(TripExpense)
class TripExpenseAdmin(admin.ModelAdmin):
    """Accounting table listing driver disbursements on active trips."""
    list_display = ['id', 'trip', 'driver', 'expense_type', 'amount', 'currency', 'recorded_at']
    list_filter = ['expense_type']
    raw_id_fields = ['trip', 'driver']


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    """Fuel logging view monitoring cost-leakages explicitly."""
    list_display = ['id', 'trip', 'vehicle', 'fuel_amount_liters', 'total_cost', 'logged_at']
    raw_id_fields = ['trip', 'vehicle', 'driver']


@admin.register(DeliveryProof)
class DeliveryProofAdmin(admin.ModelAdmin):
    """Evidence vault mapping cryptographic or photographic signatures gating 'Delivered' states."""
    list_display = ['id', 'drop_point', 'trip', 'driver', 'proof_type', 'submitted_at', 'verified_by']
    list_filter = ['proof_type']
    raw_id_fields = ['drop_point', 'trip', 'driver', 'verified_by']
