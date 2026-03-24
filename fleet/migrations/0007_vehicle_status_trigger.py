from django.db import migrations


# ---------------------------------------------------------------------------
# PostgreSQL trigger function + trigger
#
# Business rules (fire on INSERT, UPDATE of status, or DELETE):
#   • If any issue for the vehicle has status IN
#       ('reported', 'acknowledged', 'in_repair')
#     → set vehicles.status = 'under_maintenance'
#
#   • If ALL issues for the vehicle are 'resolved'
#     (or no issues remain after a deletion)
#     → set vehicles.status = 'available'
#
# Multiple-issue safety: the trigger checks the full set of remaining
# open issues for the vehicle, so resolving one issue never accidentally
# clears "under_maintenance" while other issues are still open.
# ---------------------------------------------------------------------------

CREATE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION sync_vehicle_status_from_issue()
RETURNS TRIGGER AS $$
DECLARE
    v_vehicle_id INTEGER;
    open_issue_count INTEGER;
BEGIN
    -- Resolve the vehicle FK depending on operation type
    IF TG_OP = 'DELETE' THEN
        v_vehicle_id := OLD.vehicle_id;
    ELSE
        v_vehicle_id := NEW.vehicle_id;
    END IF;

    -- Count all non-resolved issues that are still open for this vehicle.
    -- Because this is an AFTER trigger the current row already reflects the
    -- new status value (or has been removed for DELETE).
    SELECT COUNT(*)
    INTO open_issue_count
    FROM vehicle_issues
    WHERE vehicle_id = v_vehicle_id
      AND status IN ('reported', 'acknowledged', 'in_repair');

    IF open_issue_count > 0 THEN
        UPDATE vehicles
        SET    status     = 'under_maintenance',
               updated_at = NOW()
        WHERE  id = v_vehicle_id;
    ELSE
        -- No open issues remain → mark vehicle available
        UPDATE vehicles
        SET    status     = 'available',
               updated_at = NOW()
        WHERE  id = v_vehicle_id;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_vehicle_status_from_issue ON vehicle_issues;

CREATE TRIGGER trg_vehicle_status_from_issue
AFTER INSERT OR UPDATE OF status OR DELETE
ON vehicle_issues
FOR EACH ROW
EXECUTE FUNCTION sync_vehicle_status_from_issue();
"""

DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_vehicle_status_from_issue ON vehicle_issues;
"""

DROP_FUNCTION_SQL = """
DROP FUNCTION IF EXISTS sync_vehicle_status_from_issue();
"""


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0006_inspection_approved_vehicle_capacity_litre_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_FUNCTION_SQL + CREATE_TRIGGER_SQL,
            reverse_sql=DROP_TRIGGER_SQL + DROP_FUNCTION_SQL,
        ),
    ]
