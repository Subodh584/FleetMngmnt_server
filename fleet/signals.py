"""
Signals for the fleet app.

Notification rules:
  • VehicleIssue created (status='reported')
      → notify fleet managers only.
        Maintenance staff should NOT be notified yet — the manager must
        first review the issue and explicitly redirect to maintenance.

  • VehicleIssue status changes to 'in_repair'
      → notify maintenance staff.
        This happens when the fleet manager clicks "Redirect to Maintenance",
        meaning the issue has been approved and actioned.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from comms.models import Notification
from .models import VehicleIssue

User = get_user_model()


def _push_ws(user, alert_type, title, body, reference_id, reference_type):
    """
    Helper function executing the asynchronous Redis/Channels broadcast.
    Fires a JSON object representing the UI Notification payload 
    straight into the exact WebSockets group matching the `user_id`.
    Errors are safely bypassed to prevent disrupting the core database transaction.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}_notifications',
                {
                    'type': 'push_notification',
                    'data': {
                        'alert_type': alert_type,
                        'title': title,
                        'body': body,
                        'reference_id': reference_id,
                        'reference_type': reference_type,
                    },
                },
            )
    except Exception:
        pass


def _bulk_notify(recipients, alert_type, title, body, reference_id, reference_type):
    """
    Compiles database-level archival logs of incoming messages across an array of users 
    simultaneously, prior to triggering instant WebSocket push delivery routines for each.
    """
    notifications = [
        Notification(
            user=user,
            alert_type=alert_type,
            title=title,
            body=body,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        for user in recipients
    ]
    # Commit DB notifications economically
    Notification.objects.bulk_create(notifications)

    # Dispatch web-socket events
    for user in recipients:
        _push_ws(user, alert_type, title, body, reference_id, reference_type)


@receiver(post_save, sender=VehicleIssue)
def vehicle_issue_notification(sender, instance, created, **kwargs):
    """
    Listens globally for database lifecycle events triggered by VehicleIssue saves.
    Responsible for executing state-machine based communication flows for the issue lifecycle.
    """
    if created:
        # ── New issue reported ──────────────────────────────────────────────
        # Only fleet managers need to know at this point; they will decide
        # whether to redirect to maintenance.  Maintenance staff are notified
        # separately once the manager actions the issue (status → in_repair).
        recipients = list(User.objects.filter(
            profile__role='fleet_manager',
            is_active=True,
        ))
        
        _bulk_notify(
            recipients,
            alert_type='issue_reported',
            title=f'New vehicle issue: {instance.title}',
            body=f'Vehicle: {instance.vehicle}. Severity: {instance.get_severity_display()}. Awaiting your review.',
            reference_id=instance.id,
            reference_type='vehicle_issue',
        )

    else:
        # ── Status changed to in_repair ─────────────────────────────────────
        # The fleet manager has redirected the vehicle to maintenance.
        # Now notify maintenance staff so they can physically act on it.
        if instance.status == 'in_repair':
            recipients = list(User.objects.filter(
                profile__role='maintenance_staff',
                is_active=True,
            ))
            
            _bulk_notify(
                recipients,
                alert_type='maintenance_required',
                title=f'Vehicle assigned for repair: {instance.vehicle}',
                body=f'Issue: {instance.title}. Severity: {instance.get_severity_display()}.',
                reference_id=instance.id,
                reference_type='vehicle_issue',
            )
