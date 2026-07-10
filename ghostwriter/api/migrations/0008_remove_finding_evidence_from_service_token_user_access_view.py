from importlib import import_module

from django.db import migrations


DROP_SERVICE_TOKEN_USER_ACCESS_VIEW = """
DROP VIEW IF EXISTS api_service_token_user_access;
"""


FINDING_EVIDENCE_USER_ACCESS_SELECT = """
UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    reporting_evidence.uploaded_by_id AS user_id
FROM api_service_token_project_access
INNER JOIN reporting_report
    ON reporting_report.project_id = api_service_token_project_access.project_id
INNER JOIN reporting_reportfindinglink
    ON reporting_reportfindinglink.report_id = reporting_report.id
INNER JOIN reporting_evidence
    ON reporting_evidence.finding_id = reporting_reportfindinglink.id
WHERE reporting_evidence.uploaded_by_id IS NOT NULL
"""


previous_migration = import_module("ghostwriter.api.migrations.0007_service_token_user_access_view")

CREATE_PREVIOUS_SERVICE_TOKEN_USER_ACCESS_VIEW = previous_migration.CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW
CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW = CREATE_PREVIOUS_SERVICE_TOKEN_USER_ACCESS_VIEW.replace(
    FINDING_EVIDENCE_USER_ACCESS_SELECT,
    "",
)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0007_service_token_user_access_view"),
        ("reporting", "0069_remove_finding_evidence"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_SERVICE_TOKEN_USER_ACCESS_VIEW + CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW,
            reverse_sql=DROP_SERVICE_TOKEN_USER_ACCESS_VIEW,
        )
    ]
