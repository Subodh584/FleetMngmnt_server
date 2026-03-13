from django.contrib import admin

from .models import Geofence, Location, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'is_active', 'first_time_login', 'created_at']
    list_filter = ['role', 'is_active', 'first_time_login']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone']
    raw_id_fields = ['user']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'latitude', 'longitude', 'is_warehouse', 'created_at']
    list_filter = ['is_warehouse']
    search_fields = ['name', 'address']


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'center_lat', 'center_lng', 'radius_meters', 'created_by']
    search_fields = ['name']
    raw_id_fields = ['location', 'created_by']
