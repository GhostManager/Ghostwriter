"""Do not mark oplog entries stale when Hasura re-saves unchanged rows."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("oplog", "0024_oplog_sanitization_audit")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION oplog_set_entry_updated_at()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    IF TG_OP = 'INSERT' THEN
                        NEW.updated_at = clock_timestamp();
                    ELSIF current_setting('oplog.recording_change', true) = 'true'
                        OR (to_jsonb(NEW) - 'updated_at') IS DISTINCT FROM (to_jsonb(OLD) - 'updated_at') THEN
                        NEW.updated_at = clock_timestamp();
                    ELSE
                        NEW.updated_at = OLD.updated_at;
                    END IF;
                    RETURN NEW;
                END;
                $$;

                CREATE OR REPLACE FUNCTION oplog_touch_entry_for_recording_change()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    PERFORM set_config('oplog.recording_change', 'true', true);

                    IF TG_OP = 'UPDATE' AND OLD.oplog_entry_id IS DISTINCT FROM NEW.oplog_entry_id THEN
                        UPDATE oplog_oplogentry SET updated_at = clock_timestamp() WHERE id = OLD.oplog_entry_id;
                    END IF;

                    IF TG_OP = 'DELETE' THEN
                        UPDATE oplog_oplogentry SET updated_at = clock_timestamp() WHERE id = OLD.oplog_entry_id;
                    ELSE
                        UPDATE oplog_oplogentry SET updated_at = clock_timestamp() WHERE id = NEW.oplog_entry_id;
                    END IF;

                    PERFORM set_config('oplog.recording_change', 'false', true);
                    RETURN NULL;
                END;
                $$;
            """,
            reverse_sql="""
                CREATE OR REPLACE FUNCTION oplog_set_entry_updated_at()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    NEW.updated_at = clock_timestamp();
                    RETURN NEW;
                END;
                $$;

                CREATE OR REPLACE FUNCTION oplog_touch_entry_for_recording_change()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    IF TG_OP = 'UPDATE' AND OLD.oplog_entry_id IS DISTINCT FROM NEW.oplog_entry_id THEN
                        UPDATE oplog_oplogentry SET updated_at = clock_timestamp() WHERE id = OLD.oplog_entry_id;
                    END IF;

                    IF TG_OP = 'DELETE' THEN
                        UPDATE oplog_oplogentry SET updated_at = clock_timestamp() WHERE id = OLD.oplog_entry_id;
                    ELSE
                        UPDATE oplog_oplogentry SET updated_at = clock_timestamp() WHERE id = NEW.oplog_entry_id;
                    END IF;
                    RETURN NULL;
                END;
                $$;
            """,
        )
    ]
