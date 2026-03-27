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
    """Helper: fire a WebSocket push to a single user, silently ignoring errors."""
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
    """Create DB notifications and push WebSocket messages for a queryset of users."""
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
    Notification.objects.bulk_create(notifications)

    for user in recipients:
        _push_ws(user, alert_type, title, body, reference_id, reference_type)


@receiver(post_save, sender=VehicleIssue)
def vehicle_issue_notification(sender, instance, created, **kwargs):
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
        # Now notify maintenance staff so they can act on it.
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
