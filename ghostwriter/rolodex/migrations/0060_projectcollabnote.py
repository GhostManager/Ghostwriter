# Generated manually for ProjectCollabNote model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("rolodex", "0059_merge_20251027_1706"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectCollabNote",
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
                    "title",
                    models.CharField(
                        help_text="Title of the note or folder",
                        max_length=255,
                        verbose_name="Title",
                    ),
                ),
                (
                    "node_type",
                    models.CharField(
                        choices=[("folder", "Folder"), ("note", "Note")],
                        default="note",
                        help_text="Whether this is a folder or a note",
                        max_length=10,
                        verbose_name="Type",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Rich text content (for notes only, empty for folders)",
                        verbose_name="Content",
                    ),
                ),
                (
                    "position",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Order within parent (lower values first)",
                        verbose_name="Position",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent folder (null for root-level items)",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="rolodex.projectcollabnote",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        help_text="The project this note belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collab_notes",
                        to="rolodex.project",
                    ),
                ),
            ],
            options={
                "verbose_name": "Project collaborative note",
                "verbose_name_plural": "Project collaborative notes",
                "ordering": ["position", "title"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectcollabnote",
            constraint=models.CheckConstraint(
                check=models.Q(("node_type", "note")) | models.Q(("content", "")),
                name="folder_has_no_content",
            ),
        ),
    ]
