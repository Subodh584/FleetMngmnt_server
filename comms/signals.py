"""
Signals for the comms app.
Broadcast SOS alerts to all fleet managers in real time.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification, SOSAlert

User = get_user_model()


@receiver(post_save, sender=SOSAlert)
def sos_alert_notification(sender, instance, created, **kwargs):
    """
    Hooks directly into the DB lifecycle of SOSAlert instantiations natively.
    Synchronously forces the generation of high-visibility unread Database Notifications for every 
    active Fleet Manager globally, while also attempting an asynchronous push-layer WebSocket broadcast instantly.
    """
    if not created:
        return

    # Dynamically resolve absolute authority nodes globally mapping across the whole organizational identity layer.
    fleet_managers = User.objects.filter(
        profile__role='fleet_manager', is_active=True,
    )

    notifications = []
    for user in fleet_managers:
        notifications.append(
            Notification(
                user=user,
                alert_type='sos',
                title=f'SOS Alert from {instance.driver.get_full_name() or instance.driver.username}',
                body=instance.message or 'Emergency alert triggered!',
                reference_id=instance.id,
                reference_type='sos_alert',
            )
        )

    # Ingest entire array natively scaling via single blocking SQL boundary
    Notification.objects.bulk_create(notifications)

    # Push concurrently out to WebSockets ensuring visual immediate dashboard interruptions
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            for user in fleet_managers:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}_notifications',
                    {
                        'type': 'push_notification',
                        'data': {
                            'alert_type': 'sos',
                            'title': f'SOS Alert from {instance.driver.get_full_name() or instance.driver.username}',
                            'body': instance.message or 'Emergency alert triggered!',
                            'reference_id': instance.id,
                            'reference_type': 'sos_alert',
                            'latitude': str(instance.latitude),
                            'longitude': str(instance.longitude),
                        },
                    },
                )
    except Exception:
        # Never fail a critical SOS insert just because standard web-sockets dropped out randomly natively
        pass
