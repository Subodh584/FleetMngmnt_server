from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0004_add_receipt_image_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='rejection_reason',
            field=models.TextField(blank=True, default=''),
        ),
    ]
