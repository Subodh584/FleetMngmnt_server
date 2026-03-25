"""
Migration 0004 — Fix spare_parts table schema.

Migration 0002 was FAKED (table pre-existed). Its recorded state described
`maintenance` as NOT NULL/CASCADE and field types as CharField/Decimal.
The actual DB has text columns and may still have maintenance_id NOT NULL.
This migration aligns the real DB schema with the current model:
  - maintenance_id  → nullable (so spare parts can exist without a maintenance record)
  - part_name       → TEXT / NOT NULL  (already text in DB, just sync state)
  - part_number     → TEXT / NULL      (already text in DB)
  - quantity        → TEXT / NULL      (was Decimal in faked migration, actually text in DB)
  - unit_cost       → TEXT / NULL      (same as above)
  - created_at      → nullable         (model has null=True)
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0003_sparepart_add_columns'),
    ]

    operations = [
        # ── 1. Make maintenance_id nullable in the actual DB ─────────────────
        migrations.RunSQL(
            sql="ALTER TABLE spare_parts ALTER COLUMN maintenance_id DROP NOT NULL;",
            # Reverse: restore NOT NULL (only safe when all rows have a value)
            reverse_sql="ALTER TABLE spare_parts ALTER COLUMN maintenance_id SET NOT NULL;",
        ),

        # ── 2. Allow NULL on part_number, quantity, unit_cost ────────────────
        migrations.RunSQL(
            sql="""
                ALTER TABLE spare_parts
                    ALTER COLUMN part_number  DROP NOT NULL,
                    ALTER COLUMN quantity     DROP NOT NULL,
                    ALTER COLUMN unit_cost    DROP NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE spare_parts
                    ALTER COLUMN part_number  SET NOT NULL,
                    ALTER COLUMN quantity     SET NOT NULL,
                    ALTER COLUMN unit_cost    SET NOT NULL;
            """,
        ),

        # ── 3. Convert quantity / unit_cost columns to TEXT (if they are
        #       still Decimal/Numeric from the legacy schema). This is a
        #       no-op when the columns are already TEXT. ─────────────────────
        migrations.RunSQL(
            sql="""
                ALTER TABLE spare_parts
                    ALTER COLUMN quantity  TYPE text USING quantity::text,
                    ALTER COLUMN unit_cost TYPE text USING unit_cost::text;
            """,
            reverse_sql="""
                ALTER TABLE spare_parts
                    ALTER COLUMN quantity  TYPE numeric(10,2) USING quantity::numeric,
                    ALTER COLUMN unit_cost TYPE numeric(10,2) USING unit_cost::numeric;
            """,
        ),

        # ── 4. Allow NULL on created_at (model has null=True) ────────────────
        migrations.RunSQL(
            sql="ALTER TABLE spare_parts ALTER COLUMN created_at DROP NOT NULL;",
            reverse_sql="ALTER TABLE spare_parts ALTER COLUMN created_at SET NOT NULL;",
        ),

        # ── 5. Sync Django migration STATE with the model ────────────────────
        #       (so makemigrations stays clean going forward)
        migrations.AlterField(
            model_name='sparepart',
            name='maintenance',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='parts',
                to='maintenance.maintenancerecord',
            ),
        ),
        migrations.AlterField(
            model_name='sparepart',
            name='part_name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='sparepart',
            name='part_number',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sparepart',
            name='quantity',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sparepart',
            name='unit_cost',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sparepart',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
