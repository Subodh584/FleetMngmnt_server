from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    """
    Permission class to restrict API endpoint access solely to Users holding 
    the 'driver' role. Actively verifies authentication and profile linkage.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'driver'
        )


class IsFleetManager(BasePermission):
    """
    Permission class granting exclusive access to administrative users 
    designated as 'fleet_manager'. Typically utilized for sensitive actions 
    like account edits or global dashboard reads.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'fleet_manager'
        )


class IsMaintenanceStaff(BasePermission):
    """
    Permission class blocking access to any user except those explicitly labeled 
    as 'maintenance_staff'. Usually secured on workflows referencing spare parts and repairs.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'maintenance_staff'
        )


class IsFleetManagerOrReadOnly(BasePermission):
    """
    Dual-layer permission class ensuring that any authenticated profile can view 
    the resource (GET, HEAD, OPTIONS), but only 'fleet_manager' profiles have 
    clearance to mutate (POST, PUT, DELETE) the resource.
    """

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user and request.user.is_authenticated
            
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'fleet_manager'
        )


class IsMaintenanceStaffOrFleetManager(BasePermission):
    """
    Joint permission wrapper facilitating functional overlap where both 
    'maintenance_staff' and 'fleet_manager' require concurrent privileges 
    to interact with operational objects.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role in ('maintenance_staff', 'fleet_manager')
        )
