from django.contrib import admin

from .models import Geofence, Location, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for the UserProfile model.
    Provides list display, filtering, and search functionalities
    based on the user's role, contact info, and activity status.
    """
    list_display = ['user', 'role', 'phone', 'is_active', 'first_time_login', 'created_at']
    list_filter = ['role', 'is_active', 'first_time_login']
    
    # Search fields span relations using double underscores
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone']
    
    # Use raw_id_fields to avoid large dropdowns for User foreign keys
    raw_id_fields = ['user']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Location model.
    Highlights coordinates, warehouse status, and location name/address.
    """
    list_display = ['name', 'address', 'latitude', 'longitude', 'is_warehouse', 'created_at']
    list_filter = ['is_warehouse']
    search_fields = ['name', 'address']


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Geofence model.
    Shows the center coordinates, radius size, and associated location context.
    """
    list_display = ['name', 'location', 'center_lat', 'center_lng', 'radius_meters', 'created_by']
    search_fields = ['name']
    
    # Use raw_id_fields to optimize admin panel loading times for foreign key fields
    raw_id_fields = ['location', 'created_by']
