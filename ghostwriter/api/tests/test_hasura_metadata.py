# Standard Libraries
from pathlib import Path

# Django Imports
from django.test import SimpleTestCase

# 3rd Party Libraries
import yaml

# Ghostwriter Libraries
from ghostwriter.api.urls import urlpatterns
from ghostwriter.api.views import HasuraActionView

REPO_ROOT = Path(__file__).resolve().parents[3]
HASURA_METADATA_DIR = REPO_ROOT / "hasura-docker" / "metadata"
HASURA_TABLE_DIR = HASURA_METADATA_DIR / "databases" / "default" / "tables"

SENSITIVE_TABLES_WITHOUT_SERVICE_SELECT = {
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "django_content_type",
    "django_q_task",
    "home_userprofile",
    "rolodex_clientinvite",
    "rolodex_projectinvite",
    "taggit_tag",
    "taggit_taggeditem",
    "users_user_groups",
    "users_user_user_permissions",
}

READ_OPLOG_ID_HEADER = "X-Hasura-Read-Oplog-Id"
READ_PROJECT_IDS_HEADER = "X-Hasura-Read-Project-Ids"
CREATE_OPLOGENTRY_OPLOG_ID_HEADER = "X-Hasura-Create-OplogEntry-Oplog-Id"
UPDATE_OPLOGENTRY_OPLOG_ID_HEADER = "X-Hasura-Update-OplogEntry-Oplog-Id"
DELETE_OPLOGENTRY_OPLOG_ID_HEADER = "X-Hasura-Delete-OplogEntry-Oplog-Id"
SERVICE_TOKEN_ID_HEADER = "X-Hasura-Service-Token-Id"

DISALLOWED_SERVICE_HEADERS = {
    "X-Hasura-User-Id",
    "X-Hasura-Allowed-Oplog-Id",
    "X-Hasura-Allowed-Project-Id",
    "X-Hasura-Read-Project-Id",
    READ_PROJECT_IDS_HEADER,
    "X-Hasura-Create-Oplog-Id",
}


def project_scope_filter(*path):
    """
    Return a service-token project-read filter for an existing path to Project.

    Existing expectations use ``project_id`` when the table had a direct project
    FK and ``id`` when the path already ended at Project. Normalize both cases
    to the Project relationship so service tokens can use the DB-backed access
    view instead of a project-ID session-variable array.
    """
    normalized_path = list(path)
    if normalized_path and normalized_path[-1] == "project_id":
        normalized_path[-1] = "project"
    elif normalized_path and normalized_path[-1] == "id":
        normalized_path.pop()
    return service_token_project_access_filter(*normalized_path)


def service_token_project_access_filter(*path):
    expression = {
        "serviceTokenProjectAccesses": {"token_id": {"_eq": SERVICE_TOKEN_ID_HEADER}}
    }
    for segment in reversed(path):
        expression = {segment: expression}
    return expression


def evidence_project_filter():
    return {
        "_or": [
            project_scope_filter("finding", "report", "project_id"),
            project_scope_filter("report", "project_id"),
        ]
    }


def report_template_project_filter():
    return {
        "_or": [
            {"client_id": {"_is_null": True}},
            project_scope_filter("client", "projects", "id"),
        ]
    }


def domain_project_filter():
    return {
        "_or": [
            project_scope_filter("checkouts", "project_id"),
            project_scope_filter("checkouts", "domainServerConnections", "project_id"),
        ]
    }


def users_project_filter():
    return {
        "_and": [
            {"is_active": {"_eq": True}},
            {
                "_or": [
                    project_scope_filter("assignments", "project_id"),
                    project_scope_filter("cloudServers", "project_id"),
                    project_scope_filter("domainCheckouts", "project_id"),
                    {"domainNotes": {"domain": domain_project_filter()}},
                    {"domains": domain_project_filter()},
                    {"evidences": evidence_project_filter()},
                    project_scope_filter("projectNotes", "project_id"),
                    project_scope_filter("projects", "id"),
                    project_scope_filter(
                        "reportedFindingNotes", "finding", "report", "project_id"
                    ),
                    project_scope_filter("reportedFindings", "report", "project_id"),
                    project_scope_filter(
                        "reportedObservations", "report", "project_id"
                    ),
                    project_scope_filter("reports", "project_id"),
                    project_scope_filter("serverCheckouts", "project_id"),
                    project_scope_filter(
                        "serverNotes", "staticServer", "checkouts", "project_id"
                    ),
                    project_scope_filter("servers", "checkouts", "project_id"),
                ]
            },
        ]
    }


def user_feature_flag_check(flag_name):
    return {
        "_exists": {
            "_table": {"name": "users_user", "schema": "public"},
            "_where": {
                "_and": [
                    {"id": {"_eq": "X-Hasura-User-Id"}},
                    {flag_name: {"_eq": True}},
                ]
            },
        }
    }


EXPECTED_SERVICE_SELECT_FILTERS = {
    "api_service_token_project_access": {"token_id": {"_eq": SERVICE_TOKEN_ID_HEADER}},
    "commandcenter_companyinformation": {},
    "commandcenter_extrafieldmodel": {},
    "commandcenter_extrafieldspec": {},
    "commandcenter_reportconfiguration": {},
    "oplog_oplog": {
        "_or": [
            {"id": {"_eq": READ_OPLOG_ID_HEADER}},
            service_token_project_access_filter("project"),
        ]
    },
    "oplog_oplogentry": {
        "_or": [
            {"oplog_id_id": {"_eq": READ_OPLOG_ID_HEADER}},
            service_token_project_access_filter("log", "project"),
        ]
    },
    "oplog_oplogentryevidence": {
        "_and": [
            {"evidence": evidence_project_filter()},
            {"oplogEntry": project_scope_filter("log", "project_id")},
        ]
    },
    "oplog_oplogentryrecording": {
        "oplogEntry": project_scope_filter("log", "project_id")
    },
    "reporting_archive": project_scope_filter("project_id"),
    "reporting_doctype": {},
    "reporting_evidence": evidence_project_filter(),
    "reporting_finding": {},
    "reporting_findingnote": {},
    "reporting_findingtype": {},
    "reporting_localfindingnote": project_scope_filter(
        "finding", "report", "project_id"
    ),
    "reporting_observation": {},
    "reporting_report": service_token_project_access_filter("project"),
    "reporting_reportfindinglink": project_scope_filter("report", "project_id"),
    "reporting_reportobservationlink": project_scope_filter("report", "project_id"),
    "reporting_reporttemplate": report_template_project_filter(),
    "reporting_severity": {},
    "rolodex_client": project_scope_filter("projects", "id"),
    "rolodex_clientcontact": project_scope_filter("client", "projects", "id"),
    "rolodex_clientnote": project_scope_filter("client", "projects", "id"),
    "rolodex_deconfliction": project_scope_filter("project_id"),
    "rolodex_deconflictionstatus": {},
    "rolodex_objectivepriority": {},
    "rolodex_objectivestatus": {},
    "rolodex_project": service_token_project_access_filter(),
    "rolodex_projectassignment": project_scope_filter("project_id"),
    "rolodex_projectcontact": project_scope_filter("project_id"),
    "rolodex_projectnote": project_scope_filter("project_id"),
    "rolodex_projectobjective": project_scope_filter("project_id"),
    "rolodex_projectrole": {},
    "rolodex_projectscope": project_scope_filter("project_id"),
    "rolodex_projectsubtask": project_scope_filter("objective", "project_id"),
    "rolodex_projecttarget": project_scope_filter("project_id"),
    "rolodex_projecttype": {},
    "rolodex_whitecard": project_scope_filter("project_id"),
    "shepherd_activitytype": {},
    "shepherd_auxserveraddress": {},
    "shepherd_domain": {},
    "shepherd_domainnote": {},
    "shepherd_domainserverconnection": project_scope_filter("project_id"),
    "shepherd_domainstatus": {},
    "shepherd_healthstatus": {},
    "shepherd_history": project_scope_filter("project_id"),
    "shepherd_serverhistory": project_scope_filter("project_id"),
    "shepherd_servernote": {},
    "shepherd_serverprovider": {},
    "shepherd_serverrole": {},
    "shepherd_serverstatus": {},
    "shepherd_staticserver": {},
    "shepherd_transientserver": project_scope_filter("project_id"),
    "shepherd_whoisstatus": {},
    "users_user": users_project_filter(),
}

EXPECTED_SERVICE_SELECT_TABLES = set(EXPECTED_SERVICE_SELECT_FILTERS)


def load_yaml(path):
    with path.open() as handle:
        return yaml.safe_load(handle)


def table_metadata():
    for path in sorted(HASURA_TABLE_DIR.glob("public_*.yaml")):
        data = load_yaml(path)
        yield path, data


def get_service_select_permission(table):
    return next(
        (
            permission
            for permission in table.get("select_permissions", [])
            if permission.get("role") == "service"
        ),
        None,
    )


def get_service_permission(table, permission_type):
    return next(
        (
            permission
            for permission in table.get(permission_type, [])
            if permission.get("role") == "service"
        ),
        None,
    )


def get_role_permission(table, role, permission_type):
    return next(
        (
            permission
            for permission in table.get(permission_type, [])
            if permission.get("role") == role
        ),
        None,
    )


def iter_scalar_values(value):
    if isinstance(value, dict):
        for nested_value in value.values():
            yield from iter_scalar_values(nested_value)
    elif isinstance(value, list):
        for nested_value in value:
            yield from iter_scalar_values(nested_value)
    else:
        yield value


def action_path(action):
    handler = action["definition"]["handler"]
    return handler.split("}}/", 1)[1]


def view_class_for_action_path(path):
    for urlpattern in urlpatterns:
        if urlpattern.pattern.match(path):
            callback = urlpattern.callback
            return getattr(callback, "view_class", None)
    return None


class HasuraMetadataServiceRoleTests(SimpleTestCase):
    """Validate service-token Hasura metadata stays explicitly scoped."""

    def test_service_select_tables_match_project_read_contract(self):
        service_select_tables = {
            table["table"]["name"]
            for _, table in table_metadata()
            if get_service_select_permission(table)
        }

        self.assertSetEqual(service_select_tables, EXPECTED_SERVICE_SELECT_TABLES)

    def test_sensitive_tables_do_not_grant_service_select(self):
        service_select_tables = {
            table["table"]["name"]
            for _, table in table_metadata()
            if get_service_select_permission(table)
        }

        self.assertFalse(
            SENSITIVE_TABLES_WITHOUT_SERVICE_SELECT & service_select_tables,
            "Sensitive tables unexpectedly grant service select permissions",
        )

    def test_service_select_permissions_match_expected_scope_filters(self):
        mismatched_tables = {}
        for _, table in table_metadata():
            table_name = table["table"]["name"]
            service_select_permission = get_service_select_permission(table)
            if not service_select_permission:
                continue

            expected_filter = EXPECTED_SERVICE_SELECT_FILTERS[table_name]
            actual_filter = service_select_permission["permission"].get("filter")
            if actual_filter != expected_filter:
                mismatched_tables[table_name] = {
                    "expected": expected_filter,
                    "actual": actual_filter,
                }

        self.assertEqual(mismatched_tables, {})

    def test_project_metadata_has_service_token_project_access_relationship(self):
        project_metadata = load_yaml(HASURA_TABLE_DIR / "public_rolodex_project.yaml")
        service_token_relationships = [
            relationship
            for relationship in project_metadata.get("array_relationships", [])
            if relationship.get("name") == "serviceTokenProjectAccesses"
        ]

        self.assertEqual(
            service_token_relationships,
            [
                {
                    "name": "serviceTokenProjectAccesses",
                    "using": {
                        "manual_configuration": {
                            "column_mapping": {"id": "project_id"},
                            "insertion_order": None,
                            "remote_table": {
                                "name": "api_service_token_project_access",
                                "schema": "public",
                            },
                        }
                    },
                }
            ],
        )

    def test_service_permissions_do_not_use_user_or_legacy_scope_headers(self):
        unexpected_header_uses = []
        for _, table in table_metadata():
            table_name = table["table"]["name"]
            for permission_type in (
                "select_permissions",
                "insert_permissions",
                "update_permissions",
                "delete_permissions",
            ):
                for permission in table.get(permission_type, []):
                    if permission.get("role") != "service":
                        continue
                    values = set(iter_scalar_values(permission.get("permission", {})))
                    unexpected_headers = values & DISALLOWED_SERVICE_HEADERS
                    if unexpected_headers:
                        unexpected_header_uses.append(
                            (table_name, permission_type, sorted(unexpected_headers))
                        )

        self.assertEqual(unexpected_header_uses, [])

    def test_service_mutations_are_limited_to_oplog_entries(self):
        service_mutations = set()
        for _, table in table_metadata():
            table_name = table["table"]["name"]
            for permission_type in (
                "insert_permissions",
                "update_permissions",
                "delete_permissions",
            ):
                if get_service_permission(table, permission_type):
                    service_mutations.add((table_name, permission_type))

        self.assertSetEqual(
            service_mutations,
            {
                ("oplog_oplogentry", "insert_permissions"),
                ("oplog_oplogentry", "update_permissions"),
                ("oplog_oplogentry", "delete_permissions"),
            },
        )

    def test_service_oplog_entry_mutations_use_action_specific_headers(self):
        table = load_yaml(HASURA_TABLE_DIR / "public_oplog_oplogentry.yaml")

        insert_permission = get_service_permission(table, "insert_permissions")[
            "permission"
        ]
        self.assertEqual(
            insert_permission["check"],
            {"oplog_id_id": {"_eq": CREATE_OPLOGENTRY_OPLOG_ID_HEADER}},
        )

        update_permission = get_service_permission(table, "update_permissions")[
            "permission"
        ]
        self.assertEqual(
            update_permission["filter"],
            {"oplog_id_id": {"_eq": UPDATE_OPLOGENTRY_OPLOG_ID_HEADER}},
        )
        self.assertEqual(
            update_permission["check"],
            {"oplog_id_id": {"_eq": UPDATE_OPLOGENTRY_OPLOG_ID_HEADER}},
        )

        delete_permission = get_service_permission(table, "delete_permissions")[
            "permission"
        ]
        self.assertEqual(
            delete_permission["filter"],
            {"oplog_id_id": {"_eq": DELETE_OPLOGENTRY_OPLOG_ID_HEADER}},
        )

    def test_service_checkouts_remain_project_scoped(self):
        expected_checkout_filters = {
            "public_shepherd_history.yaml": project_scope_filter("project_id"),
            "public_shepherd_serverhistory.yaml": project_scope_filter("project_id"),
            "public_shepherd_domainserverconnection.yaml": project_scope_filter(
                "project_id"
            ),
        }

        for filename, expected_filter in expected_checkout_filters.items():
            table = load_yaml(HASURA_TABLE_DIR / filename)
            service_select_permission = get_service_select_permission(table)

            self.assertEqual(
                service_select_permission["permission"].get("filter"),
                expected_filter,
                filename,
            )

    def test_user_role_cannot_query_background_tasks(self):
        table = load_yaml(HASURA_TABLE_DIR / "public_django_q_task.yaml")

        self.assertIsNone(get_role_permission(table, "user", "select_permissions"))

    def test_recording_text_select_access_is_explicit(self):
        table = load_yaml(HASURA_TABLE_DIR / "public_oplog_oplogentryrecording.yaml")
        expected_columns = [
            "id",
            "oplog_entry_id",
            "recording_file",
            "recording_text",
            "uploaded_by_id",
            "uploaded_date",
        ]

        for role in ("manager", "user", "service"):
            permission = get_role_permission(table, role, "select_permissions")
            self.assertEqual(
                permission["permission"].get("columns"),
                expected_columns,
                role,
            )

    def test_service_actions_require_explicit_django_authorization(self):
        actions_metadata = load_yaml(HASURA_METADATA_DIR / "actions.yaml")
        service_actions = [
            action
            for action in actions_metadata["actions"]
            if any(
                permission.get("role") == "service"
                for permission in action.get("permissions", [])
            )
        ]
        actions_missing_authorization = []

        for action in service_actions:
            view_class = view_class_for_action_path(action_path(action))
            if view_class is None or not issubclass(view_class, HasuraActionView):
                actions_missing_authorization.append(action["name"])
                continue

            has_static_requirements = bool(
                getattr(view_class, "service_token_permission_requirements", ())
            )
            overrides_requirements = (
                view_class.get_service_token_permission_requirements
                is not HasuraActionView.get_service_token_permission_requirements
            )
            if not has_static_requirements and not overrides_requirements:
                actions_missing_authorization.append(action["name"])

        self.assertEqual(actions_missing_authorization, [])


class HasuraMetadataUserRoleTests(SimpleTestCase):
    """Validate user-role Hasura metadata for app-level RBAC contracts."""

    def test_library_write_permissions_require_user_feature_flags(self):
        expectations = {
            "public_reporting_finding.yaml": {
                "insert_permissions": ("check", "enable_finding_create"),
                "update_permissions": ("check", "enable_finding_edit"),
                "delete_permissions": ("filter", "enable_finding_delete"),
            },
            "public_reporting_observation.yaml": {
                "insert_permissions": ("check", "enable_observation_create"),
                "update_permissions": ("check", "enable_observation_edit"),
                "delete_permissions": ("filter", "enable_observation_delete"),
            },
        }

        for filename, permission_expectations in expectations.items():
            table = load_yaml(HASURA_TABLE_DIR / filename)
            for permission_type, (
                check_field,
                feature_flag,
            ) in permission_expectations.items():
                permission = get_role_permission(table, "user", permission_type)
                self.assertEqual(
                    permission["permission"].get(check_field),
                    user_feature_flag_check(feature_flag),
                    f"{filename} {permission_type}",
                )
