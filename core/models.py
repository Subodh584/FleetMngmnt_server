from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Extends Django's built-in User with fleet-specific fields."""

    ROLE_CHOICES = [
        ('driver', 'Driver'),
        ('fleet_manager', 'Fleet Manager'),
        ('maintenance_staff', 'Maintenance Staff'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    DRIVER_STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_trip', 'In Trip'),
        ('clocked_out', 'Clocked Out'),
        ('on_rest', 'On Rest'),
        ('on_leave', 'On Leave'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True, default='')
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    first_time_login = models.BooleanField(default=True)
    driver_status = models.CharField(
        max_length=20,
        choices=DRIVER_STATUS_CHOICES,
        default='clocked_out',
    )
    rest_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def resolve_rest_status(self):
        """If the rest window has elapsed, automatically flip status to available."""
        from django.utils import timezone
        if self.driver_status == 'on_rest' and self.rest_ends_at and timezone.now() >= self.rest_ends_at:
            self.driver_status = 'available'
            self.rest_ends_at = None
            self.save(update_fields=['driver_status', 'rest_ends_at', 'updated_at'])

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_role_display()})'


class DriverDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('aadhar', 'Aadhaar Card'),
        ('driving_license', 'Driving License'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents',
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='driver_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'driver_documents'

    def __str__(self):
        return f'{self.get_document_type_display()} – {self.user}'


class ProfileImage(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile_image_obj',
    )
    image = models.ImageField(upload_to='profile_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profile_images'

    def __str__(self):
        return f'Profile image – {self.user}'


class Location(models.Model):
    """Warehouses, drop points, and generic locations."""

    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default='')
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    is_warehouse = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'locations'

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_requests',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_leave_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Leave #{self.pk} – {self.driver} ({self.start_date} → {self.end_date})'


class Geofence(models.Model):
    """Circular geofence around a location."""

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='geofences',
        null=True, blank=True,
    )
    name = models.CharField(max_length=200)
    center_lat = models.DecimalField(max_digits=10, decimal_places=7)
    center_lng = models.DecimalField(max_digits=10, decimal_places=7)
    radius_meters = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_geofences',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'geofences'

    def __str__(self):
        return self.name
