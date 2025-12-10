"""Add AI review storage to projects."""

# Generated manually due to offline environment
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rolodex", "0094_add_ad_threshold_mappings"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="ai_review",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="AI-generated review summaries organized by scoped subcards",
            ),
        ),
    ]
