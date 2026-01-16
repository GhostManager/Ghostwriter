# Data migration: Migrate existing Project.collab_note content to ProjectCollabNote

from django.db import migrations


def migrate_existing_notes(apps, schema_editor):
    """Migrate existing collab_note content to new hierarchical model."""
    Project = apps.get_model("rolodex", "Project")
    ProjectCollabNote = apps.get_model("rolodex", "ProjectCollabNote")

    for project in Project.objects.exclude(collab_note="").exclude(collab_note__isnull=True):
        ProjectCollabNote.objects.create(
            project=project,
            parent=None,
            title="Migrated Notes",
            node_type="note",
            content=project.collab_note,
            position=0,
        )


def reverse_migration(apps, schema_editor):
    """Reverse: copy first note back to collab_note field."""
    Project = apps.get_model("rolodex", "Project")
    ProjectCollabNote = apps.get_model("rolodex", "ProjectCollabNote")

    for project in Project.objects.all():
        first_note = ProjectCollabNote.objects.filter(
            project=project,
            node_type="note",
        ).order_by("position", "title").first()
        if first_note:
            project.collab_note = first_note.content
            project.save(update_fields=["collab_note"])


class Migration(migrations.Migration):

    dependencies = [
        ("rolodex", "0060_projectcollabnote"),
    ]

    operations = [
        migrations.RunPython(migrate_existing_notes, reverse_migration),
    ]
