from django.db import migrations


CREATE_SERVICE_TOKEN_DOMAIN_ACCESS_VIEW = """
CREATE VIEW api_service_token_domain_access AS
SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_history.domain_id
FROM api_service_token_project_access
INNER JOIN shepherd_history
    ON shepherd_history.project_id = api_service_token_project_access.project_id
WHERE shepherd_history.domain_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_history.domain_id
FROM api_service_token_project_access
INNER JOIN shepherd_domainserverconnection
    ON shepherd_domainserverconnection.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_history
    ON shepherd_history.id = shepherd_domainserverconnection.domain_id
WHERE shepherd_history.domain_id IS NOT NULL
"""


CREATE_SERVICE_TOKEN_STATIC_SERVER_ACCESS_VIEW = """
CREATE VIEW api_service_token_static_server_access AS
SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_serverhistory.server_id
FROM api_service_token_project_access
INNER JOIN shepherd_serverhistory
    ON shepherd_serverhistory.project_id = api_service_token_project_access.project_id
WHERE shepherd_serverhistory.server_id IS NOT NULL

UNION

SELECT DISTINCT
    api_service_token_project_access.token_id,
    shepherd_serverhistory.server_id
FROM api_service_token_project_access
INNER JOIN shepherd_domainserverconnection
    ON shepherd_domainserverconnection.project_id = api_service_token_project_access.project_id
INNER JOIN shepherd_serverhistory
    ON shepherd_serverhistory.id = shepherd_domainserverconnection.static_server_id
WHERE shepherd_serverhistory.server_id IS NOT NULL
"""


DROP_SERVICE_TOKEN_INFRASTRUCTURE_ACCESS_VIEWS = """
DROP VIEW IF EXISTS api_service_token_static_server_access;
DROP VIEW IF EXISTS api_service_token_domain_access;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0009_service_token_client_project_scope"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                CREATE_SERVICE_TOKEN_DOMAIN_ACCESS_VIEW
                + ";"
                + CREATE_SERVICE_TOKEN_STATIC_SERVER_ACCESS_VIEW
            ),
            reverse_sql=DROP_SERVICE_TOKEN_INFRASTRUCTURE_ACCESS_VIEWS,
        )
    ]
