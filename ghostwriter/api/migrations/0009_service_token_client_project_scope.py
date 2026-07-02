from importlib import import_module

from django.db import migrations, models


DROP_SERVICE_TOKEN_USER_ACCESS_VIEW = """
DROP VIEW IF EXISTS api_service_token_user_access;
"""


CREATE_SERVICE_TOKEN_PROJECT_ACCESS_VIEW = """
CREATE OR REPLACE VIEW api_service_token_project_access AS
SELECT DISTINCT
    api_servicetokenpermission.token_id,
    api_servicetokenpermission.resource_id AS project_id
FROM api_servicetokenpermission
INNER JOIN api_servicetoken
    ON api_servicetoken.id = api_servicetokenpermission.token_id
INNER JOIN api_serviceprincipal
    ON api_serviceprincipal.id = api_servicetoken.service_principal_id
INNER JOIN users_user AS token_creator
    ON token_creator.id = api_servicetoken.created_by_id
INNER JOIN users_user AS service_principal_creator
    ON service_principal_creator.id = api_serviceprincipal.created_by_id
INNER JOIN api_user_project_read_access
    ON api_user_project_read_access.user_id = api_servicetoken.created_by_id
    AND api_user_project_read_access.project_id = api_servicetokenpermission.resource_id
WHERE
    api_servicetokenpermission.resource_type = 'project'
    AND api_servicetokenpermission.action = 'read'
    AND api_servicetokenpermission.resource_id IS NOT NULL
    AND api_servicetokenpermission.constraints = '{}'::jsonb
    AND NOT api_servicetoken.revoked
    AND (
        api_servicetoken.expiry_date IS NULL
        OR api_servicetoken.expiry_date >= NOW()
    )
    AND api_serviceprincipal.active
    AND token_creator.is_active
    AND service_principal_creator.is_active

UNION

SELECT DISTINCT
    api_servicetoken.id AS token_id,
    api_user_project_read_access.project_id
FROM api_servicetoken
INNER JOIN api_servicetokenpermission
    ON api_servicetokenpermission.token_id = api_servicetoken.id
INNER JOIN api_serviceprincipal
    ON api_serviceprincipal.id = api_servicetoken.service_principal_id
INNER JOIN users_user AS token_creator
    ON token_creator.id = api_servicetoken.created_by_id
INNER JOIN users_user AS service_principal_creator
    ON service_principal_creator.id = api_serviceprincipal.created_by_id
INNER JOIN api_user_project_read_access
    ON api_user_project_read_access.user_id = api_servicetoken.created_by_id
INNER JOIN rolodex_project
    ON rolodex_project.id = api_user_project_read_access.project_id
    AND rolodex_project.client_id = api_servicetokenpermission.resource_id
WHERE
    api_servicetokenpermission.resource_type = 'client'
    AND api_servicetokenpermission.action = 'read'
    AND api_servicetokenpermission.resource_id IS NOT NULL
    AND api_servicetokenpermission.constraints = '{}'::jsonb
    AND NOT api_servicetoken.revoked
    AND (
        api_servicetoken.expiry_date IS NULL
        OR api_servicetoken.expiry_date >= NOW()
    )
    AND api_serviceprincipal.active
    AND token_creator.is_active
    AND service_principal_creator.is_active

UNION

SELECT DISTINCT
    api_servicetoken.id AS token_id,
    api_user_project_read_access.project_id
FROM api_servicetoken
INNER JOIN api_servicetokenpermission
    ON api_servicetokenpermission.token_id = api_servicetoken.id
INNER JOIN api_serviceprincipal
    ON api_serviceprincipal.id = api_servicetoken.service_principal_id
INNER JOIN users_user AS token_creator
    ON token_creator.id = api_servicetoken.created_by_id
INNER JOIN users_user AS service_principal_creator
    ON service_principal_creator.id = api_serviceprincipal.created_by_id
INNER JOIN api_user_project_read_access
    ON api_user_project_read_access.user_id = api_servicetoken.created_by_id
WHERE
    api_servicetokenpermission.resource_type = 'project'
    AND api_servicetokenpermission.action = 'read'
    AND api_servicetokenpermission.resource_id IS NULL
    AND api_servicetokenpermission.constraints = '{"scope": "all_accessible_projects"}'::jsonb
    AND NOT api_servicetoken.revoked
    AND (
        api_servicetoken.expiry_date IS NULL
        OR api_servicetoken.expiry_date >= NOW()
    )
    AND api_serviceprincipal.active
    AND token_creator.is_active
    AND service_principal_creator.is_active
"""


previous_project_access_migration = import_module(
    "ghostwriter.api.migrations.0003_service_token_project_access_views"
)
previous_user_access_migration = import_module(
    "ghostwriter.api.migrations.0008_remove_finding_evidence_from_service_token_user_access_view"
)

CREATE_PREVIOUS_SERVICE_TOKEN_PROJECT_ACCESS_VIEW = (
    previous_project_access_migration.CREATE_SERVICE_TOKEN_PROJECT_ACCESS_VIEW
)
CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW = (
    previous_user_access_migration.CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW
)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_remove_finding_evidence_from_service_token_user_access_view"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="servicetokenpermission",
            name="api_stp_allowed_resource_action",
        ),
        migrations.AlterField(
            model_name="servicetokenpermission",
            name="resource_type",
            field=models.CharField(
                choices=[
                    ("client", "Client"),
                    ("oplog", "Oplog"),
                    ("project", "Project"),
                ],
                max_length=64,
            ),
        ),
        migrations.AddConstraint(
            model_name="servicetokenpermission",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("action__in", ["read", "create", "update", "delete"]),
                        ("resource_type", "oplog"),
                    )
                    | models.Q(("action", "read"), ("resource_type", "project"))
                    | models.Q(("action", "read"), ("resource_type", "client"))
                ),
                name="api_stp_allowed_resource_action",
            ),
        ),
        migrations.RunSQL(
            sql=(
                DROP_SERVICE_TOKEN_USER_ACCESS_VIEW
                + CREATE_SERVICE_TOKEN_PROJECT_ACCESS_VIEW
                + ";"
                + CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW
            ),
            reverse_sql=(
                DROP_SERVICE_TOKEN_USER_ACCESS_VIEW
                + CREATE_PREVIOUS_SERVICE_TOKEN_PROJECT_ACCESS_VIEW
                + ";"
                + CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW
            ),
        ),
    ]
