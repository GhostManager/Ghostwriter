
from django.db import migrations

FIELDS = [
    ('reporting_evidence', 'friendly_name'),
    ('reporting_finding', 'cvss_vector'),
    ('reporting_finding', 'description'),
    ('reporting_finding', 'finding_guidance'),
    ('reporting_finding', 'host_detection_techniques'),
    ('reporting_finding', 'impact'),
    ('reporting_finding', 'mitigation'),
    ('reporting_finding', 'network_detection_techniques'),
    ('reporting_finding', 'references'),
    ('reporting_finding', 'replication_steps'),
    ('reporting_findingnote', 'note'),
    ('reporting_localfindingnote', 'note'),
    ('reporting_observation', 'description'),
    ('reporting_reportfindinglink', 'affected_entities'),
    ('reporting_reportfindinglink', 'cvss_vector'),
    ('reporting_reportfindinglink', 'description'),
    ('reporting_reportfindinglink', 'finding_guidance'),
    ('reporting_reportfindinglink', 'host_detection_techniques'),
    ('reporting_reportfindinglink', 'impact'),
    ('reporting_reportfindinglink', 'mitigation'),
    ('reporting_reportfindinglink', 'network_detection_techniques'),
    ('reporting_reportfindinglink', 'references'),
    ('reporting_reportfindinglink', 'replication_steps'),
    ('reporting_reportobservationlink', 'description'),
    ('reporting_reporttemplate', 'changelog'),
    ('reporting_reporttemplate', 'name'),
    ('reporting_reporttemplate', 'p_style'),
]

SQL_UP = "\n".join(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{column}\" SET DEFAULT '';" for (table, column) in FIELDS)
SQL_DOWN = "\n".join(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{column}\" DROP DEFAULT;" for (table, column) in FIELDS)

class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0053_alter_evidence_document'),
    ]

    operations = [
        migrations.RunSQL(SQL_UP, reverse_sql=SQL_DOWN),
    ]
