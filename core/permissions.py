from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    """Allow access only to users with the 'driver' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'driver'
        )


class IsFleetManager(BasePermission):
    """Allow access only to users with the 'fleet_manager' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'fleet_manager'
        )


class IsMaintenanceStaff(BasePermission):
    """Allow access only to users with the 'maintenance_staff' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'maintenance_staff'
        )


class IsFleetManagerOrReadOnly(BasePermission):
    """Fleet managers can write; everyone else is read-only."""

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
    """Allow access to maintenance_staff or fleet_manager."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role in ('maintenance_staff', 'fleet_manager')
        )
