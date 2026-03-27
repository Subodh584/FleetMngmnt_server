from django.db import migrations


# ---------------------------------------------------------------------------
# Updated trigger — vehicle status is set to 'under_maintenance' only when
# a fleet manager has actively acted on an issue ('acknowledged' or
# 'in_repair').  A freshly-reported issue ('reported') no longer changes the
# vehicle status automatically; the fleet manager must explicitly redirect
# the vehicle to maintenance via the "Redirect to Maintenance" action.
# ---------------------------------------------------------------------------

CREATE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION sync_vehicle_status_from_issue()
RETURNS TRIGGER AS $$
DECLARE
    v_vehicle_id INTEGER;
    active_issue_count INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_vehicle_id := OLD.vehicle_id;
    ELSE
        v_vehicle_id := NEW.vehicle_id;
    END IF;

    -- Only count issues that a manager has acknowledged or that are actively
    -- being repaired.  'reported' issues alone do NOT lock the vehicle.
    SELECT COUNT(*)
    INTO active_issue_count
    FROM vehicle_issues
    WHERE vehicle_id = v_vehicle_id
      AND status IN ('acknowledged', 'in_repair');

    IF active_issue_count > 0 THEN
        UPDATE vehicles
        SET    status     = 'under_maintenance',
               updated_at = NOW()
        WHERE  id = v_vehicle_id;
    ELSE
        -- No active issues remain → mark vehicle available
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

# Revert to the original behaviour (reported also triggers under_maintenance)
REVERT_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION sync_vehicle_status_from_issue()
RETURNS TRIGGER AS $$
DECLARE
    v_vehicle_id INTEGER;
    open_issue_count INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_vehicle_id := OLD.vehicle_id;
    ELSE
        v_vehicle_id := NEW.vehicle_id;
    END IF;

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


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0008_inspection_maintenance_scheduled_status'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_FUNCTION_SQL + CREATE_TRIGGER_SQL,
            reverse_sql=REVERT_FUNCTION_SQL + CREATE_TRIGGER_SQL,
        ),
    ]
