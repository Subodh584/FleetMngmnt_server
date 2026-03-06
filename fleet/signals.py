"""
Signals for the fleet app.
Notify maintenance staff when a vehicle issue is reported.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from comms.models import Notification
from .models import VehicleIssue

User = get_user_model()


@receiver(post_save, sender=VehicleIssue)
def vehicle_issue_notification(sender, instance, created, **kwargs):
    """Notify all maintenance staff when a new vehicle issue is reported."""
    if not created:
        return

    # Find all maintenance staff
    maintenance_users = User.objects.filter(
        profile__role='maintenance_staff', is_active=True,
    )

    notifications = []
    for user in maintenance_users:
        notifications.append(
            Notification(
                user=user,
                alert_type='issue_reported',
                title=f'New issue: {instance.title}',
                body=f'Vehicle: {instance.vehicle}. Severity: {instance.get_severity_display()}.',
                reference_id=instance.id,
                reference_type='vehicle_issue',
            )
        )

    Notification.objects.bulk_create(notifications)

    # Push via WebSocket
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            for user in maintenance_users:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}_notifications',
                    {
                        'type': 'push_notification',
                        'data': {
                            'alert_type': 'issue_reported',
                            'title': f'New issue: {instance.title}',
                            'body': f'Vehicle: {instance.vehicle}. Severity: {instance.get_severity_display()}.',
                            'reference_id': instance.id,
                            'reference_type': 'vehicle_issue',
                        },
                    },
                )
    except Exception:
        pass
