from django.db import migrations


CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW = """
CREATE VIEW api_service_token_user_access AS
SELECT DISTINCT
    api_service_token_project_access.token_id,
    rolodex_projectassignment.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN rolodex_projectassignment
    ON rolodex_projectassignment.project_id = api_service_token_project_access.project_id
WHERE rolodex_projectassignment.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_transientserver.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_transientserver
    ON shepherd_transientserver.project_id = api_service_token_project_access.project_id
WHERE shepherd_transientserver.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_history.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_history
    ON shepherd_history.project_id = api_service_token_project_access.project_id
WHERE shepherd_history.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_domainnote.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_history
    ON shepherd_history.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_domainnote
    ON shepherd_domainnote.domain_id = shepherd_history.domain_id
WHERE shepherd_domainnote.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_domainnote.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_domainserverconnection
    ON shepherd_domainserverconnection.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_history
    ON shepherd_history.id = shepherd_domainserverconnection.domain_id
INNER JOIN shepherd_domainnote
    ON shepherd_domainnote.domain_id = shepherd_history.domain_id
WHERE shepherd_domainnote.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_domain.last_used_by_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_history
    ON shepherd_history.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_domain
    ON shepherd_domain.id = shepherd_history.domain_id
WHERE shepherd_domain.last_used_by_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_domain.last_used_by_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_domainserverconnection
    ON shepherd_domainserverconnection.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_history
    ON shepherd_history.id = shepherd_domainserverconnection.domain_id
INNER JOIN shepherd_domain
    ON shepherd_domain.id = shepherd_history.domain_id
WHERE shepherd_domain.last_used_by_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    reporting_evidence.uploaded_by_id AS user_id
FROM api_service_token_project_access
INNER JOIN reporting_report
    ON reporting_report.project_id = api_service_token_project_access.project_id
INNER JOIN reporting_evidence
    ON reporting_evidence.report_id = reporting_report.id
WHERE reporting_evidence.uploaded_by_id IS NOT NULL

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

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    rolodex_projectnote.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN rolodex_projectnote
    ON rolodex_projectnote.project_id = api_service_token_project_access.project_id
WHERE rolodex_projectnote.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    rolodex_project.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN rolodex_project
    ON rolodex_project.id = api_service_token_project_access.project_id
WHERE rolodex_project.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    reporting_localfindingnote.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN reporting_report
    ON reporting_report.project_id = api_service_token_project_access.project_id
INNER JOIN reporting_reportfindinglink
    ON reporting_reportfindinglink.report_id = reporting_report.id
INNER JOIN reporting_localfindingnote
    ON reporting_localfindingnote.finding_id = reporting_reportfindinglink.id
WHERE reporting_localfindingnote.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    reporting_reportfindinglink.assigned_to_id AS user_id
FROM api_service_token_project_access
INNER JOIN reporting_report
    ON reporting_report.project_id = api_service_token_project_access.project_id
INNER JOIN reporting_reportfindinglink
    ON reporting_reportfindinglink.report_id = reporting_report.id
WHERE reporting_reportfindinglink.assigned_to_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    reporting_reportobservationlink.assigned_to_id AS user_id
FROM api_service_token_project_access
INNER JOIN reporting_report
    ON reporting_report.project_id = api_service_token_project_access.project_id
INNER JOIN reporting_reportobservationlink
    ON reporting_reportobservationlink.report_id = reporting_report.id
WHERE reporting_reportobservationlink.assigned_to_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    reporting_report.created_by_id AS user_id
FROM api_service_token_project_access
INNER JOIN reporting_report
    ON reporting_report.project_id = api_service_token_project_access.project_id
WHERE reporting_report.created_by_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_serverhistory.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_serverhistory
    ON shepherd_serverhistory.project_id = api_service_token_project_access.project_id
WHERE shepherd_serverhistory.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_servernote.operator_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_serverhistory
    ON shepherd_serverhistory.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_servernote
    ON shepherd_servernote.server_id = shepherd_serverhistory.server_id
WHERE shepherd_servernote.operator_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_staticserver.last_used_by_id AS user_id
FROM api_service_token_project_access
INNER JOIN shepherd_serverhistory
    ON shepherd_serverhistory.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_staticserver
    ON shepherd_staticserver.id = shepherd_serverhistory.server_id
WHERE shepherd_staticserver.last_used_by_id IS NOT NULL
"""


DROP_SERVICE_TOKEN_USER_ACCESS_VIEW = """
DROP VIEW IF EXISTS api_service_token_user_access;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_apikey_last_used_at"),
        ("reporting", "0067_alter_reporttemplate_evidence_image_width"),
        ("rolodex", "0063_alter_project_collab_note"),
        ("shepherd", "0052_rename_note_to_description"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW,
            reverse_sql=DROP_SERVICE_TOKEN_USER_ACCESS_VIEW,
        )
    ]
