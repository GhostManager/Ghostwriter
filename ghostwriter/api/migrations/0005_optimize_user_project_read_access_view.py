# Django Imports
from django.db import migrations

CREATE_OPTIMIZED_USER_PROJECT_READ_ACCESS_VIEW = """
CREATE OR REPLACE VIEW api_user_project_read_access AS
SELECT
    privileged_users.id AS user_id,
    rolodex_project.id AS project_id
FROM (
    SELECT id
    FROM users_user
    WHERE
        users_user.is_active
        AND (
            users_user.role IN ('admin', 'manager')
            OR users_user.is_staff
            OR users_user.is_superuser
        )
) AS privileged_users
INNER JOIN rolodex_project
    ON TRUE

UNION

SELECT
    rolodex_clientinvite.user_id,
    rolodex_project.id AS project_id
FROM rolodex_clientinvite
INNER JOIN users_user
    ON users_user.id = rolodex_clientinvite.user_id
    AND users_user.is_active
INNER JOIN rolodex_project
    ON rolodex_project.client_id = rolodex_clientinvite.client_id

UNION

SELECT
    rolodex_projectinvite.user_id,
    rolodex_projectinvite.project_id
FROM rolodex_projectinvite
INNER JOIN users_user
    ON users_user.id = rolodex_projectinvite.user_id
    AND users_user.is_active

UNION

SELECT
    rolodex_projectassignment.operator_id AS user_id,
    rolodex_projectassignment.project_id
FROM rolodex_projectassignment
INNER JOIN users_user
    ON users_user.id = rolodex_projectassignment.operator_id
    AND users_user.is_active
"""


CREATE_ORIGINAL_USER_PROJECT_READ_ACCESS_VIEW = """
CREATE OR REPLACE VIEW api_user_project_read_access AS
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


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_apikey_opaque_tokens_and_user_sessions"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_OPTIMIZED_USER_PROJECT_READ_ACCESS_VIEW,
            reverse_sql=CREATE_ORIGINAL_USER_PROJECT_READ_ACCESS_VIEW,
        )
    ]
