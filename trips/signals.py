"""
Signals for the trips app.
Push notifications when trip status changes.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from comms.models import Notification
from .models import Trip


@receiver(post_save, sender=Trip)
def trip_status_notification(sender, instance, created, **kwargs):
    """
    Listens for Trip saving events natively within Django's ORM.
    Dispatches persistent DB notifications and ephemeral WebSocket pushes universally 
    when drivers get assigned new trips or whenever the state transitions.
    """
    if created:
        title = f'New trip assigned: {instance.order.order_ref}'
        body = f'Vehicle: {instance.vehicle}. Check your trips for details.'
        alert_type = 'geofence_entry'  # reusing closest alert_type
    else:
        title = f'Trip {instance.order.order_ref} status: {instance.get_status_display()}'
        body = ''
        alert_type = 'route_deviation'

    notification = Notification.objects.create(
        user=instance.driver,
        alert_type=alert_type,
        title=title,
        body=body,
        reference_id=instance.id,
        reference_type='trip',
    )

    # Push immediately via WebSocket
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'user_{instance.driver_id}_notifications',
                {
                    'type': 'push_notification',
                    'data': {
                        'id': notification.id,
                        'alert_type': notification.alert_type,
                        'title': notification.title,
                        'body': notification.body,
                        'reference_id': notification.reference_id,
                        'reference_type': notification.reference_type,
                        'created_at': str(notification.created_at),
                    },
                },
            )
    except Exception:
        pass  # Don't break the parent save context if channel layer is unreachable
