"""
Signals for the core app.
Auto-create UserProfile when a User is created.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile for every new User (default role: driver)."""
    if created and not hasattr(instance, '_skip_profile_creation'):
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': 'driver'},
        )
