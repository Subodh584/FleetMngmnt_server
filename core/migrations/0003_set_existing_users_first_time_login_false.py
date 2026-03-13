"""
Data migration: set first_time_login=False for all existing UserProfile rows.
"""

from django.db import migrations


def set_existing_false(apps, schema_editor):
    UserProfile = apps.get_model('core', 'UserProfile')
    UserProfile.objects.all().update(first_time_login=False)


def reverse_noop(apps, schema_editor):
    pass  # no meaningful reverse


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_userprofile_first_time_login'),
    ]

    operations = [
        migrations.RunPython(set_existing_false, reverse_noop),
    ]
