from django.conf import settings
from django.db import models


class Message(models.Model):
    """
    Structured payload tracking internal 1:1 chat messages natively between User accounts.
    Strictly ties operational dialogue directly back to specific Trip execution blocks.
    """
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages',
    )
    trip = models.ForeignKey(
        'trips.Trip', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='messages',
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['receiver', 'is_read'], name='idx_messages_receiver'),
            models.Index(fields=['trip'], name='idx_messages_trip'),
        ]
        ordering = ['-sent_at']

    def __str__(self):
        return f'Message from {self.sender} to {self.receiver}'


class Notification(models.Model):
    """
    Global unified logging struct mapping asynchronous alerts for iOS/Web Dashboards.
    Allows decoupling system events securely from physical asset logic natively.
    """
    ALERT_TYPE_CHOICES = [
        ('sos', 'SOS'),
        ('route_deviation', 'Route Deviation'),
        ('geofence_entry', 'Geofence Entry'),
        ('geofence_exit', 'Geofence Exit'),
        ('maintenance_due', 'Maintenance Due'),
        ('issue_reported', 'Issue Reported'),
        ('trip_rejected', 'Trip Rejected'),
        ('leave_approved', 'Leave Approved'),
        ('leave_rejected', 'Leave Rejected'),
        ('leave_request', 'Leave Request'),
    ]
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications',
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    
    # Generic pointers connecting alerts seamlessly to originating objects securely.
    reference_id = models.IntegerField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, blank=True, default='')
    
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_notifications_user'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.alert_type}: {self.title}'


class SOSAlert(models.Model):
    """
    Critical escalation pathway.
    Tracks panic-button physical triggers pressed natively by Drivers in transit.
    Forces explicit human audit resolution chains natively before clearing.
    """
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sos_alerts',
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='sos_alerts',
    )
    trip = models.ForeignKey(
        'trips.Trip', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sos_alerts',
    )
    
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    message = models.TextField(blank=True, default='')
    
    # Mandatory operational resolution locking.
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='resolved_sos_alerts',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sos_alerts'
        ordering = ['-triggered_at']

    def __str__(self):
        return f'SOS #{self.pk} – {self.driver}'
