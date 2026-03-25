from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0003_order_capacity_kg_order_capacity_litre_odometerimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuellog',
            name='receipt_image',
            field=models.ImageField(blank=True, null=True, upload_to='fuel_receipts/'),
        ),
        migrations.AddField(
            model_name='tripexpense',
            name='receipt_image',
            field=models.ImageField(blank=True, null=True, upload_to='expense_receipts/'),
        ),

    ]
