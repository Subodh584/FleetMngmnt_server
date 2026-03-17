from django.db import migrations


def seed_pre_trip_checklist(apps, schema_editor):
    InspectionChecklist = apps.get_model('fleet', 'InspectionChecklist')
    InspectionChecklistItem = apps.get_model('fleet', 'InspectionChecklistItem')

    checklist, created = InspectionChecklist.objects.get_or_create(
        name='Pre-Trip Inspection',
        defaults={'is_active': True},
    )
    if created:
        items = [
            ('Tire Condition & Pressure', 1),
            ('Brake Condition & Response', 2),
            ('Lights & Blinkers', 3),
            ('Fuel Level', 4),
            ('Engine Condition', 5),
        ]
        InspectionChecklistItem.objects.bulk_create([
            InspectionChecklistItem(
                checklist=checklist,
                item_name=name,
                sequence_no=seq,
                is_required=True,
            )
            for name, seq in items
        ])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(seed_pre_trip_checklist, noop),
    ]
