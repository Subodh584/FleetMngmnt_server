from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0006_alter_trip_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('assigned', 'Assigned'),
                    ('accepted', 'Accepted'),
                    ('in_progress', 'In Progress'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('rejected', 'Rejected'),
                    ('delayed', 'Delayed'),
                ],
                default='assigned',
                max_length=20,
            ),
        ),
    ]
