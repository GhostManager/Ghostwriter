# Django Imports
from django.db import migrations

CREATE_USER_PROJECT_READ_ACCESS_VIEW = """
CREATE VIEW api_user_project_read_access AS
SELECT DISTINCT
    users_user.id AS user_id,
    rolodex_project.id AS project_id
FROM users_user
CROSS JOIN rolodex_project
WHERE
    users_user.is_active
    AND (
        users_user.role IN ('admin', 'manager')
        OR users_user.is_staff
        OR users_user.is_superuser
        OR EXISTS (
            SELECT 1
            FROM rolodex_clientinvite
            WHERE
                rolodex_clientinvite.user_id = users_user.id
                AND rolodex_clientinvite.client_id = rolodex_project.client_id
        )
        OR EXISTS (
            SELECT 1
            FROM rolodex_projectinvite
            WHERE
                rolodex_projectinvite.user_id = users_user.id
                AND rolodex_projectinvite.project_id = rolodex_project.id
        )
        OR EXISTS (
            SELECT 1
            FROM rolodex_projectassignment
            WHERE
                rolodex_projectassignment.operator_id = users_user.id
                AND rolodex_projectassignment.project_id = rolodex_project.id
        )
    )
"""


CREATE_SERVICE_TOKEN_PROJECT_ACCESS_VIEW = """
CREATE VIEW api_service_token_project_access AS
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


DROP_VIEWS = """
DROP VIEW IF EXISTS api_service_token_project_access;
DROP VIEW IF EXISTS api_user_project_read_access;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_service_tokens"),
        ("rolodex", "0028_clientinvite_projectinvite"),
        ("users", "0013_remove_user_require_2fa_user_require_mfa"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
            {CREATE_USER_PROJECT_READ_ACCESS_VIEW};
            {CREATE_SERVICE_TOKEN_PROJECT_ACCESS_VIEW};
            """,
            reverse_sql=DROP_VIEWS,
        )
    ]
