from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0005_alter_sparepart_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenancerecord',
            name='parts_used',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
