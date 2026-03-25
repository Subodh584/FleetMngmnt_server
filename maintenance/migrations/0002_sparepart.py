from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SparePart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('part_name', models.CharField(max_length=200)),
                ('part_number', models.CharField(blank=True, default='', max_length=100)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('total_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('maintenance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='parts',
                    to='maintenance.maintenancerecord',
                )),
            ],
            options={'db_table': 'spare_parts'},
        ),
    ]
