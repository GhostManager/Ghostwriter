# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("oplog", "0022_alter_oplogentryevidence_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="oplogentryrecording",
            name="recording_text",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Searchable text extracted from the asciicast recording (input and output events, ANSI stripped).",
            ),
        ),
    ]
