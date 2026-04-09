"""Data migration to move content from Project.collab_note to ProjectCollabNote."""

from django.db import migrations


def migrate_collab_notes(apps, schema_editor):
    Project = apps.get_model("rolodex", "Project")
    ProjectCollabNote = apps.get_model("rolodex", "ProjectCollabNote")
    ProjectCollabNoteField = apps.get_model("rolodex", "ProjectCollabNoteField")

    for project in Project.objects.exclude(collab_note=""):
        note = ProjectCollabNote.objects.create(
            project=project,
            title="Notes",
            node_type="note",
            content=project.collab_note,
            position=0,
        )
        ProjectCollabNoteField.objects.create(
            note=note,
            field_type="rich_text",
            content=project.collab_note,
            position=0,
        )


def reverse_migrate(apps, schema_editor):
    ProjectCollabNote = apps.get_model("rolodex", "ProjectCollabNote")
    ProjectCollabNote.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("rolodex", "0062_projectcollabnote_projectcollabnotefield"),
    ]

    operations = [
        migrations.RunPython(migrate_collab_notes, reverse_migrate),
    ]
