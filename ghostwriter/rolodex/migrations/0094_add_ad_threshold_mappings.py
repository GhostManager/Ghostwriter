from django.db import migrations, models


def seed_ad_thresholds(apps, schema_editor):
    model = apps.get_model("rolodex", "ADThresholdMapping")
    try:
        from ghostwriter.rolodex.ad_thresholds import AD_THRESHOLD_DEFAULTS
    except Exception:
        AD_THRESHOLD_DEFAULTS = {}

    for key, meta in AD_THRESHOLD_DEFAULTS.items():
        model.objects.update_or_create(
            key=key,
            defaults={
                "label": meta.get("label") or key,
                "issue_text": meta.get("issue") or "",
                "threshold_type": meta.get("threshold_type") or "percent_of_enabled",
                "value": meta.get("value") or 0,
            },
        )


def remove_ad_thresholds(apps, schema_editor):
    model = apps.get_model("rolodex", "ADThresholdMapping")
    keys = []
    try:
        from ghostwriter.rolodex.ad_thresholds import AD_THRESHOLD_DEFAULTS

        keys = list(AD_THRESHOLD_DEFAULTS.keys())
    except Exception:
        keys = []

    if keys:
        model.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rolodex", "0093_vulnerability_web_issue_matrix"),
    ]

    operations = [
        migrations.CreateModel(
            name="ADThresholdMapping",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "key",
                    models.CharField(
                        choices=[
                            ("min_enabled_ratio", "Minimum enabled account ratio"),
                            ("generic_accounts_pct", "Generic accounts percentage of enabled accounts"),
                            ("generic_logins_pct", "Generic logins percentage of enabled accounts"),
                            ("inactive_accounts_pct", "Inactive accounts percentage of enabled accounts"),
                            ("passwords_never_exp_pct", "Passwords that never expire percentage of enabled accounts"),
                            ("exp_passwords_pct", "Expired passwords percentage of enabled accounts"),
                            ("domain_admin_pct", "Domain Admins percentage of enabled accounts"),
                            ("ent_admin_absolute", "Enterprise Admins absolute threshold"),
                        ],
                        help_text="Identifier used by CAP generation logic.",
                        max_length=64,
                        unique=True,
                        verbose_name="Threshold key",
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        help_text="Human-friendly label shown in the admin UI.",
                        max_length=128,
                        verbose_name="Label",
                    ),
                ),
                (
                    "issue_text",
                    models.CharField(
                        help_text="Issue that will be raised when the threshold is exceeded.",
                        max_length=255,
                        verbose_name="Issue text",
                    ),
                ),
                (
                    "threshold_type",
                    models.CharField(
                        choices=[
                            ("percent_of_enabled", "Percent of enabled accounts"),
                            ("min_ratio", "Minimum ratio"),
                            ("absolute", "Absolute count"),
                        ],
                        help_text="How the value should be applied (percentage, ratio, or absolute count).",
                        max_length=32,
                        verbose_name="Threshold type",
                    ),
                ),
                (
                    "value",
                    models.FloatField(
                        default=0.0,
                        help_text="Threshold value applied according to the threshold type.",
                        verbose_name="Threshold value",
                    ),
                ),
            ],
            options={
                "verbose_name": "AD threshold mapping",
                "verbose_name_plural": "AD threshold mappings",
                "ordering": ["label"],
            },
        ),
        migrations.RunPython(seed_ad_thresholds, remove_ad_thresholds),
    ]
