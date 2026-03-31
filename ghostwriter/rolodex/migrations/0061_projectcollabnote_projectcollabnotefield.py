import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rolodex", "0060_alter_clientcontact_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectCollabNote",
            fields=[
                (
                    "id",
                    models.AutoField(
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
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "updated_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
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
                check=models.Q(("node_type", "note"), ("content", ""), _connector="OR"),
                name="folder_has_no_content",
            ),
        ),
        migrations.CreateModel(
            name="ProjectCollabNoteField",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "field_type",
                    models.CharField(
                        choices=[("rich_text", "Rich Text"), ("image", "Image")],
                        default="rich_text",
                        help_text="Type of content in this field",
                        max_length=10,
                        verbose_name="Field Type",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="HTML content for rich text fields",
                        verbose_name="Content",
                    ),
                ),
                (
                    "image_width",
                    models.IntegerField(
                        blank=True,
                        editable=False,
                        null=True,
                        verbose_name="Image Width",
                    ),
                ),
                (
                    "image_height",
                    models.IntegerField(
                        blank=True,
                        editable=False,
                        null=True,
                        verbose_name="Image Height",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Image file for image fields",
                        height_field="image_height",
                        null=True,
                        upload_to="collab_note_images/%Y/%m/%d/",
                        verbose_name="Image",
                        width_field="image_width",
                    ),
                ),
                (
                    "position",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Order within note (lower values first)",
                        verbose_name="Position",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "updated_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "note",
                    models.ForeignKey(
                        help_text="The note this field belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fields",
                        to="rolodex.projectcollabnote",
                    ),
                ),
            ],
            options={
                "verbose_name": "Project collaborative note field",
                "verbose_name_plural": "Project collaborative note fields",
                "ordering": ["note", "position"],
            },
        ),
    ]
