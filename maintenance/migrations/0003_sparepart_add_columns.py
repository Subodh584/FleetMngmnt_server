from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0002_sparepart'),
    ]

    operations = [
        migrations.AddField(
            model_name='sparepart',
            name='total_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='sparepart',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
