"""Add oplog sanitization auditing and database-maintained entry timestamps."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("oplog", "0023_oplogentryrecording_recording_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="OplogSanitization",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sanitized_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                (
                    "sanitized_by_name",
                    models.CharField(
                        blank=True,
                        help_text="A display-name snapshot of the user who requested the sanitization.",
                        max_length=255,
                    ),
                ),
                (
                    "fields",
                    models.JSONField(
                        default=list,
                        help_text="The entry fields included in this sanitization.",
                    ),
                ),
                (
                    "oplog",
                    models.ForeignKey(
                        help_text="The activity log that was sanitized.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sanitizations",
                        to="oplog.oplog",
                    ),
                ),
                (
                    "sanitized_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="The user who requested the sanitization.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="oplog_sanitizations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Activity log sanitization",
                "verbose_name_plural": "Activity log sanitizations",
                "ordering": ["-sanitized_at", "-id"],
            },
        ),
        migrations.AddField(
            model_name="oplogentry",
            name="updated_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, editable=False
            ),
        ),
        migrations.AddIndex(
            model_name="oplogsanitization",
            index=models.Index(
                fields=["oplog", "-sanitized_at"], name="oplog_oplog_oplog_i_824f5e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="oplogentry",
            index=models.Index(
                fields=["oplog_id", "-updated_at"],
                name="oplog_oplog_oplog_i_0bf5d6_idx",
            ),
        ),
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION oplog_set_entry_updated_at()
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

                CREATE TRIGGER oplog_entry_set_updated_at
                BEFORE INSERT OR UPDATE ON oplog_oplogentry
                FOR EACH ROW EXECUTE FUNCTION oplog_set_entry_updated_at();

                CREATE FUNCTION oplog_touch_entry_for_recording_change()
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

                CREATE TRIGGER oplog_recording_touch_entry
                AFTER INSERT OR UPDATE OR DELETE ON oplog_oplogentryrecording
                FOR EACH ROW EXECUTE FUNCTION oplog_touch_entry_for_recording_change();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS oplog_recording_touch_entry ON oplog_oplogentryrecording;
                DROP FUNCTION IF EXISTS oplog_touch_entry_for_recording_change();
                DROP TRIGGER IF EXISTS oplog_entry_set_updated_at ON oplog_oplogentry;
                DROP FUNCTION IF EXISTS oplog_set_entry_updated_at();
            """,
        ),
    ]
