"""
Endpoint tests for the middleware API.

``test_app.py`` covers the ``/runPoc`` PoC-runner logic. This module covers the
request/response contract of every route: auth, input validation, and - most
importantly - the Python that reads GraphQL responses.

That last part is the gap the CI schema check cannot fill. ``validate_graphql.py``
proves each query still matches the Hasura schema, but it cannot prove the handler
still reads the right keys out of the result. Commit 145b5529 broke exactly that
way: evidence moved from finding-scoped to report-scoped, and because the handler
used ``.get(..., [])`` the mismatch produced empty data rather than an error.

Run from this directory:

    pip install -r requirements.txt pytest
    pytest
"""
import base64
import os

import pytest


os.environ.setdefault("FLASK_API_KEY", "test-key")
os.environ.setdefault("GHOSTWRITER_API_TOKEN", "test-token")
os.environ.setdefault("GHOSTWRITER_GRAPHQL_URL", "https://ghostwriter.test/v1/graphql")

import app as app_module  # noqa: E402


HEADERS = {"X-API-Key": "test-key"}

# Every route, with the method and a minimal valid-shaped body. Used by the
# blanket auth test so a new route cannot be added without an auth check.
ROUTES = [
    ("post", "/createClient", {"name": "Acme"}),
    ("post", "/updateClient", {"clientId": 1, "name": "Acme"}),
    ("post", "/uploadClientLogo", {"clientId": 1, "fileBase64": "eA==", "fileName": "l.png"}),
    ("get", "/getClient?clientId=1", None),
    ("post", "/createProject", {"clientId": 1, "projectTypeId": 1, "startDate": "2026-01-01", "endDate": "2026-01-02"}),
    ("post", "/updateProject", {"projectId": 1, "codename": "x"}),
    ("get", "/getProjects?clientId=1", None),
    ("get", "/getProject?projectId=1", None),
    ("post", "/createRetest", {"projectId": 1}),
    ("get", "/getStatistics?clientId=1", None),
    ("post", "/generateReport", {"projectId": 1, "templateId": 1}),
    ("post", "/runPoc", {"finding_id": 1}),
]


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class GraphQLStub:
    """
    Fake ``requests.Session.post`` that answers GraphQL calls from a routing table
    and records every (query, variables) pair for assertions.

    ``routes`` maps a substring of the query to either a ``data`` dict or a
    callable taking the variables and returning one.
    """

    def __init__(self, routes, default=None):
        self.routes = routes
        self.default = default
        self.calls = []

    # Assigned onto Session.post as a plain object, so there is no descriptor
    # binding and no implicit ``self`` for the session - ``url`` arrives first.
    def __call__(self, url, json=None, timeout=None, **kwargs):
        query = (json or {}).get("query", "")
        variables = (json or {}).get("variables", {})
        self.calls.append({"query": query, "variables": variables, "timeout": timeout})

        for needle, response in self.routes.items():
            if needle in query:
                if callable(response):
                    response = response(variables)
                if isinstance(response, FakeResponse):
                    return response
                return FakeResponse(payload={"data": response})

        if self.default is not None:
            return FakeResponse(payload={"data": self.default})
        raise AssertionError(f"unexpected graphql query: {query.strip()[:80]}")

    def queries_matching(self, needle):
        return [c for c in self.calls if needle in c["query"]]

    def variables_for(self, needle):
        matches = self.queries_matching(needle)
        assert matches, f"no graphql call matching {needle!r}"
        return matches[0]["variables"]


@pytest.fixture
def client():
    app = app_module.create_app()
    app.testing = True
    return app.test_client()


@pytest.fixture
def stub(monkeypatch):
    """Install a GraphQLStub; tests set ``.routes`` before calling the endpoint."""
    holder = GraphQLStub({})
    monkeypatch.setattr(app_module.requests.Session, "post", holder)
    return holder


def call(client, method, path, body=None):
    fn = getattr(client, method)
    if method == "get":
        return fn(path, headers=HEADERS)
    return fn(path, json=body, headers=HEADERS)


# --- Auth -------------------------------------------------------------------

@pytest.mark.parametrize("method,path,body", ROUTES, ids=[r[1].split("?")[0] for r in ROUTES])
def test_route_requires_api_key(client, method, path, body):
    fn = getattr(client, method)
    resp = fn(path) if method == "get" else fn(path, json=body)
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "unauthorized"}


@pytest.mark.parametrize("method,path,body", ROUTES, ids=[r[1].split("?")[0] for r in ROUTES])
def test_route_rejects_wrong_api_key(client, method, path, body):
    headers = {"X-API-Key": "wrong"}
    fn = getattr(client, method)
    resp = fn(path, headers=headers) if method == "get" else fn(path, json=body, headers=headers)
    assert resp.status_code == 401


# --- /createClient ----------------------------------------------------------

def test_create_client_requires_name(client):
    resp = call(client, "post", "/createClient", {})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "name is required"}


def test_create_client_happy_path(client, stub):
    stub.routes = {"insert_client_one": {"insert_client_one": {"id": 7}}}
    resp = call(client, "post", "/createClient", {
        "name": "Acme", "shortName": "ACM", "contacts": {"data": [{"name": "Bob"}]},
    })
    assert resp.status_code == 200
    assert resp.get_json() == {"insert_client_one": {"id": 7}}
    # contacts is a valid nested insert on client_insert_input and must survive.
    assert stub.variables_for("insert_client_one")["object"] == {
        "name": "Acme", "shortName": "ACM", "contacts": {"data": [{"name": "Bob"}]},
    }


def test_create_client_drops_unknown_and_logo_fields(client, stub):
    stub.routes = {"insert_client_one": {"insert_client_one": {"id": 7}}}
    call(client, "post", "/createClient", {
        "name": "Acme", "logo_base64": "eA==", "nope": "x",
    })
    obj = stub.variables_for("insert_client_one")["object"]
    assert obj == {"name": "Acme"}, "logo_base64 goes via /uploadClientLogo, unknown keys are dropped"


def test_create_client_graphql_error_is_502(client, stub):
    stub.routes = {"insert_client_one": FakeResponse(payload={"errors": [{"message": "boom"}]})}
    resp = call(client, "post", "/createClient", {"name": "Acme"})
    assert resp.status_code == 502
    assert resp.get_json()["error"]["message"] == "graphql error"


def test_create_client_missing_id_is_502(client, stub):
    stub.routes = {"insert_client_one": {"insert_client_one": {}}}
    resp = call(client, "post", "/createClient", {"name": "Acme"})
    assert resp.status_code == 502
    assert resp.get_json() == {"error": "GraphQL did not return client id"}


# --- /updateClient ----------------------------------------------------------

def test_update_client_requires_client_id(client):
    resp = call(client, "post", "/updateClient", {"name": "Acme"})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "clientId is required"}


def test_update_client_requires_fields(client):
    resp = call(client, "post", "/updateClient", {"clientId": 1})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "no fields to update"}


def test_update_client_happy_path(client, stub):
    stub.routes = {"update_client_by_pk": {"update_client_by_pk": {"id": 1, "name": "N", "shortName": "S"}}}
    resp = call(client, "post", "/updateClient", {"clientId": 1, "name": "N"})
    assert resp.status_code == 200
    assert resp.get_json()["update_client_by_pk"]["name"] == "N"
    assert stub.variables_for("update_client_by_pk") == {"clientId": 1, "set": {"name": "N"}}


def test_update_client_cannot_set_show_results_in_dashboard(client, stub):
    """The dashboard visibility flag is operator-controlled; the API must not set it."""
    stub.routes = {"update_client_by_pk": {"update_client_by_pk": {"id": 1}}}
    call(client, "post", "/updateClient", {
        "clientId": 1,
        "extraFields": {"showResultsInDashboard": True, "other": "keep"},
    })
    assert stub.variables_for("update_client_by_pk")["set"]["extraFields"] == {"other": "keep"}


def test_update_client_coerces_string_client_id(client, stub):
    stub.routes = {"update_client_by_pk": {"update_client_by_pk": {"id": 1}}}
    call(client, "post", "/updateClient", {"clientId": "1", "name": "N"})
    assert stub.variables_for("update_client_by_pk")["clientId"] == 1


@pytest.mark.xfail(reason="KNOWN BUG: contacts is read but never applied - silent no-op", strict=True)
def test_update_client_applies_contacts(client, stub):
    stub.routes = {"contact": {"insert_contact": {"affected_rows": 1}}}
    resp = call(client, "post", "/updateClient", {"clientId": 1, "contacts": [{"name": "Bob"}]})
    assert resp.status_code == 200
    assert stub.queries_matching("contact"), "contacts were accepted but no mutation was sent"


# --- /uploadClientLogo ------------------------------------------------------

@pytest.mark.parametrize("missing,expected", [
    ("clientId", "clientId is required"),
    ("fileBase64", "fileBase64 is required"),
    ("fileName", "fileName is required"),
])
def test_upload_client_logo_requires_fields(client, missing, expected):
    body = {"clientId": 1, "fileBase64": "eA==", "fileName": "logo.png"}
    del body[missing]
    resp = call(client, "post", "/uploadClientLogo", body)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": expected}


def test_upload_client_logo_rejects_non_integer_id(client):
    resp = call(client, "post", "/uploadClientLogo", {
        "clientId": "abc", "fileBase64": "eA==", "fileName": "logo.png",
    })
    assert resp.status_code == 400
    assert "clientId must be an integer" in str(resp.get_json())


def test_upload_client_logo_happy_path(client, stub):
    stub.routes = {"uploadClientLogo": {"uploadClientLogo": {"id": 3}}}
    resp = call(client, "post", "/uploadClientLogo", {
        "clientId": "1", "fileBase64": "eA==", "fileName": "logo.png",
    })
    assert resp.status_code == 200
    assert resp.get_json() == {"uploadClientLogo": {"id": 3}}
    # The action argument names differ from the REST body names.
    assert stub.variables_for("uploadClientLogo") == {
        "clientId": 1, "file_base64": "eA==", "filename": "logo.png",
    }


# --- /getClient -------------------------------------------------------------

def test_get_client_requires_client_id(client):
    resp = call(client, "get", "/getClient")
    assert resp.status_code == 400


def test_get_client_rejects_non_integer_id(client):
    resp = call(client, "get", "/getClient?clientId=abc")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "clientId must be an integer"}


def test_get_client_happy_path(client, stub):
    stub.routes = {"client_by_pk": {"client_by_pk": {"id": 1, "name": "Acme", "extraFields": {}}}}
    resp = call(client, "get", "/getClient?clientId=1")
    assert resp.status_code == 200
    assert resp.get_json()["client_by_pk"]["name"] == "Acme"
    assert stub.variables_for("client_by_pk") == {"clientId": 1}


# --- /createProject ---------------------------------------------------------

def test_create_project_reports_all_missing_fields(client):
    resp = call(client, "post", "/createProject", {"clientId": 1})
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["error"] == "missing required fields"
    assert set(payload["fields"]) == {"projectTypeId", "startDate", "endDate"}


def test_create_project_happy_path(client, stub):
    stub.routes = {"insert_project_one": {"insert_project_one": {"id": 12}}}
    resp = call(client, "post", "/createProject", {
        "clientId": 1, "projectTypeId": 2, "startDate": "2026-01-01", "endDate": "2026-01-31",
        "codename": "BLUE", "nope": "dropped",
    })
    assert resp.status_code == 200
    assert resp.get_json() == {"insert_project_one": {"id": 12}}
    obj = stub.variables_for("insert_project_one")["object"]
    assert "nope" not in obj
    assert obj["codename"] == "BLUE"


# --- /updateProject ---------------------------------------------------------

def test_update_project_requires_project_id(client):
    resp = call(client, "post", "/updateProject", {"codename": "x"})
    assert resp.status_code == 400


def test_update_project_requires_fields(client):
    resp = call(client, "post", "/updateProject", {"projectId": 1})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "no fields to update"}


def test_update_project_happy_path(client, stub):
    stub.routes = {"update_project_by_pk": {"update_project_by_pk": {"id": 1}}}
    resp = call(client, "post", "/updateProject", {"projectId": "1", "codename": "RED", "nope": 1})
    assert resp.status_code == 200
    assert stub.variables_for("update_project_by_pk") == {"projectId": 1, "set": {"codename": "RED"}}


# --- /getProjects -----------------------------------------------------------

def test_get_projects_requires_client_id(client):
    resp = call(client, "get", "/getProjects")
    assert resp.status_code == 400


def test_get_projects_happy_path(client, stub):
    stub.routes = {"ProjectsByClient": {"project": [{"id": 1, "codename": "BLUE"}]}}
    resp = call(client, "get", "/getProjects?clientId=1")
    assert resp.status_code == 200
    assert resp.get_json()["project"][0]["codename"] == "BLUE"


# --- /getProject ------------------------------------------------------------

def _project_payload(extra_fields):
    """A /getProject response with one report carrying a finding and evidence."""
    return {
        "project_by_pk": {
            "id": 1,
            "codename": "BLUE",
            "description": "desc",
            "clientId": 9,
            "client": {"id": 9, "name": "Acme", "shortName": "ACM", "extraFields": extra_fields},
            "projectType": {"id": 2, "projectType": "Pentest"},
            "reports": [{
                "id": 5,
                "title": "Report A",
                "evidence": [{"id": 77}],
                "findings": [{"id": 31, "title": "SQLi", "description": "secret detail"}],
            }],
        }
    }


def _get_project_routes(extra_fields):
    return {
        "GetProject": _project_payload(extra_fields),
        "downloadEvidence": {"downloadEvidence": {
            "evidenceId": 77, "filename": "e.png", "friendlyName": "Shot", "fileBase64": "eA==",
        }},
    }


def test_get_project_requires_project_id(client):
    resp = call(client, "get", "/getProject")
    assert resp.status_code == 400


def test_get_project_rejects_non_integer_id(client):
    resp = call(client, "get", "/getProject?projectId=abc")
    assert resp.status_code == 400


def test_get_project_returns_findings_when_flag_true(client, stub):
    stub.routes = _get_project_routes({"showResultsInDashboard": True})
    resp = call(client, "get", "/getProject?projectId=1")
    assert resp.status_code == 200
    report = resp.get_json()["project_by_pk"]["reports"][0]
    assert [f["title"] for f in report["findings"]] == ["SQLi"]
    # Evidence ids are replaced by downloaded blobs.
    assert report["evidence"] == [{
        "evidenceId": 77, "filename": "e.png", "friendlyName": "Shot", "fileBase64": "eA==",
    }]
    assert len(stub.queries_matching("downloadEvidence")) == 1


@pytest.mark.parametrize("extra_fields", [
    {"showResultsInDashboard": False},
    {},
    None,
    {"showResultsInDashboard": "true"},  # JSONB string is not a boolean true
], ids=["false", "key-absent", "null-extrafields", "string-true"])
def test_get_project_hides_findings_when_flag_not_true(client, stub, extra_fields):
    stub.routes = _get_project_routes(extra_fields)
    resp = call(client, "get", "/getProject?projectId=1")
    assert resp.status_code == 200
    report = resp.get_json()["project_by_pk"]["reports"][0]
    assert report["findings"] == []
    assert report["evidence"] == []


def test_get_project_skips_evidence_downloads_when_hidden(client, stub):
    """Hiding findings must also skip the per-evidence download round trips."""
    stub.routes = _get_project_routes({"showResultsInDashboard": False})
    call(client, "get", "/getProject?projectId=1")
    assert stub.queries_matching("downloadEvidence") == []


@pytest.mark.parametrize("extra_fields", [{"showResultsInDashboard": True}, {"showResultsInDashboard": False}])
def test_get_project_always_returns_project_details(client, stub, extra_fields):
    """The flag gates finding detail only - project, client and type always return."""
    stub.routes = _get_project_routes(extra_fields)
    project = call(client, "get", "/getProject?projectId=1").get_json()["project_by_pk"]
    assert project["codename"] == "BLUE"
    assert project["description"] == "desc"
    assert project["client"]["name"] == "Acme"
    assert project["projectType"]["projectType"] == "Pentest"
    assert project["reports"][0]["title"] == "Report A"


def test_get_project_queries_report_scoped_evidence(client, stub):
    """
    Regression guard for 145b5529: evidence is report-scoped, not finding-scoped.
    The schema check catches a bad query; this catches the handler reading the
    wrong key and silently returning nothing.
    """
    stub.routes = _get_project_routes({"showResultsInDashboard": True})
    call(client, "get", "/getProject?projectId=1")
    query = stub.queries_matching("GetProject")[0]["query"]
    assert "evidences" not in query, "evidences was the pre-145b5529 finding-scoped field"
    findings_at = query.index("findings(")
    evidence_at = query.index("evidence {")
    assert evidence_at < findings_at, "evidence must be selected on the report, not the finding"


def test_get_project_graphql_error_is_502(client, stub):
    stub.routes = {"GetProject": FakeResponse(status_code=500, text="nope")}
    resp = call(client, "get", "/getProject?projectId=1")
    assert resp.status_code == 502


# --- /createRetest ----------------------------------------------------------

ORIGINAL_PROJECT = {
    "project_by_pk": {
        "id": 1, "codename": "BLUE", "description": "d", "clientId": 9, "projectTypeId": 2,
        "startDate": "2026-01-01", "endDate": "2026-01-31", "timezone": "UTC",
        "reports": [{"findings": [
            {"id": 31, "title": "SQLi", "description": "orig", "severityId": 1},
            {"id": 32, "title": "XSS", "description": "orig2", "severityId": 2},
        ]}],
    }
}


def _retest_routes(project=None):
    return {
        "GetProjectForRetest": project if project is not None else ORIGINAL_PROJECT,
        "insert_project_one": {"insert_project_one": {"id": 100}},
        "insert_report_one": {"insert_report_one": {"id": 200}},
        "insert_reportedFinding": {"insert_reportedFinding": {
            "affected_rows": 2, "returning": [{"id": 301}, {"id": 302}],
        }},
        "uploadEvidence": {"uploadEvidence": {"id": 400}},
    }


def test_create_retest_requires_project_id(client):
    resp = call(client, "post", "/createRetest", {})
    assert resp.status_code == 400


def test_create_retest_missing_project_is_404(client, stub):
    stub.routes = _retest_routes({"project_by_pk": None})
    resp = call(client, "post", "/createRetest", {"projectId": 1})
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"]


def test_create_retest_happy_path(client, stub):
    stub.routes = _retest_routes()
    resp = call(client, "post", "/createRetest", {"projectId": 1})
    assert resp.status_code == 200
    assert resp.get_json() == {
        "originalProjectId": 1,
        "newProjectId": 100,
        "newReportId": 200,
        "findingsCopied": 2,
        "findingIdMapping": {"31": 301, "32": 302},
    }


def test_create_retest_names_and_scopes_the_copy(client, stub):
    stub.routes = _retest_routes()
    call(client, "post", "/createRetest", {"projectId": 1})
    new_project = stub.variables_for("insert_project_one")["object"]
    assert new_project["codename"] == "Retest - BLUE"
    assert new_project["clientId"] == 9
    report = stub.variables_for("insert_report_one")["object"]
    assert report == {
        "projectId": 100, "title": "Original Findings",
        "creation": "2026-01-31", "last_update": "2026-01-31",
        "archived": False, "complete": False, "delivered": False,
        "include_bloodhound_data": False,
    }
    findings = stub.variables_for("insert_reportedFinding")["objects"]
    assert [f["reportId"] for f in findings] == [200, 200]
    assert "id" not in findings[0], "original primary keys must not be copied"


def test_create_retest_applies_comment_status_and_description(client, stub):
    stub.routes = _retest_routes()
    call(client, "post", "/createRetest", {
        "projectId": 1,
        "comments": [{"findingId": 31, "status": "RESOLVED", "description": "<p>fixed</p>"}],
    })
    findings = stub.variables_for("insert_reportedFinding")["objects"]
    assert findings[0]["title"] == "RESOLVED - SQLi"
    assert "Retest Comment" in findings[0]["description"]
    assert findings[1]["title"] == "XSS", "untouched findings keep their title"


def test_create_retest_uploads_evidence_to_the_report(client, stub):
    """
    Regression guard for 145b5529: uploadEvidence takes ``report``, not ``finding``.
    """
    stub.routes = _retest_routes()
    call(client, "post", "/createRetest", {
        "projectId": 1,
        "comments": [{"findingId": 31, "evidence_b64": "eA==", "evidence_filename": "a.png"}],
    })
    variables = stub.variables_for("uploadEvidence")
    assert variables["report"] == 200
    assert "finding" not in variables
    assert variables["filename"] == "a.png"


def test_create_retest_reports_unmatched_evidence(client, stub):
    stub.routes = _retest_routes()
    resp = call(client, "post", "/createRetest", {
        "projectId": 1,
        "comments": [{"findingId": 999, "evidence_b64": "eA=="}],
    })
    assert resp.status_code == 200
    assert resp.get_json()["evidenceErrors"][0]["originalFindingId"] == 999
    assert stub.queries_matching("uploadEvidence") == []


def test_create_retest_with_no_findings_skips_insert(client, stub):
    stub.routes = _retest_routes({"project_by_pk": dict(ORIGINAL_PROJECT["project_by_pk"], reports=[])})
    resp = call(client, "post", "/createRetest", {"projectId": 1})
    assert resp.status_code == 200
    assert resp.get_json()["findingsCopied"] == 0
    assert stub.queries_matching("insert_reportedFinding") == []


# --- /getStatistics ---------------------------------------------------------

def test_get_statistics_requires_client_id(client):
    resp = call(client, "get", "/getStatistics")
    assert resp.status_code == 400


def test_get_statistics_aggregates_totals(client, stub):
    stub.routes = {
        "ClientSeverityTotals": {"findingSeverity": [
            {"id": 1, "severity": "High", "reportedFindings_aggregate": {"aggregate": {"count": 3}}},
            {"id": 2, "severity": "Low", "reportedFindings_aggregate": {"aggregate": {"count": 1}}},
        ]},
        "ProjectsFindingsByClient": {"project": [{
            "id": 1, "codename": "BLUE",
            "reports": [{"findings": [
                {"severityId": 1, "severity": {"id": 1, "severity": "High"}},
                {"severityId": 1, "severity": {"id": 1, "severity": "High"}},
                {"severityId": 2, "severity": {"id": 2, "severity": "Low"}},
            ]}],
        }]},
    }
    resp = call(client, "get", "/getStatistics?clientId=1")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["clientTotals"] == [
        {"severityId": 1, "severity": "High", "count": 3},
        {"severityId": 2, "severity": "Low", "count": 1},
    ]
    assert payload["projects"] == [{
        "id": 1, "codename": "BLUE",
        "severityTotals": [
            {"severityId": 1, "severity": "High", "count": 2},
            {"severityId": 2, "severity": "Low", "count": 1},
        ],
    }]


def test_get_statistics_filters_on_dashboard_flag(client, stub):
    """Both statistics queries must be scoped by the client's visibility flag."""
    stub.routes = {
        "ClientSeverityTotals": {"findingSeverity": []},
        "ProjectsFindingsByClient": {"project": []},
    }
    call(client, "get", "/getStatistics?clientId=1")
    for needle in ("ClientSeverityTotals", "ProjectsFindingsByClient"):
        query = stub.queries_matching(needle)[0]["query"]
        assert "showResultsInDashboard: true" in query


# --- /generateReport --------------------------------------------------------

@pytest.fixture
def fake_soffice(monkeypatch):
    """Replace the LibreOffice call with one that writes a stub PDF."""
    class Result:
        returncode = 0
        stderr = b""

    def fake_run(args, **kwargs):
        outdir = args[args.index("--outdir") + 1]
        with open(os.path.join(outdir, "report.pdf"), "wb") as fh:
            fh.write(b"%PDF-1.4 stub")
        return Result()

    monkeypatch.setattr(app_module.subprocess, "run", fake_run)


@pytest.mark.parametrize("missing", ["projectId", "templateId"])
def test_generate_report_requires_fields(client, missing):
    body = {"projectId": 1, "templateId": 2}
    del body[missing]
    resp = call(client, "post", "/generateReport", body)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": f"{missing} is required"}


def test_generate_report_rejects_non_integer_ids(client):
    resp = call(client, "post", "/generateReport", {"projectId": "abc", "templateId": 2})
    assert resp.status_code == 400


def test_generate_report_with_no_reports_returns_empty(client, stub):
    stub.routes = {"GetReports": {"report": []}}
    resp = call(client, "post", "/generateReport", {"projectId": 1, "templateId": 2})
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_generate_report_converts_docx_to_pdf(client, stub, fake_soffice):
    stub.routes = {
        "GetReports": {"report": [{"id": 5, "title": "Report A"}]},
        "generateDocReport": {"generateDocReport": {
            "docBase64": base64.b64encode(b"docx bytes").decode(),
            "fileName": "Report A.docx",
        }},
    }
    resp = call(client, "post", "/generateReport", {"projectId": 1, "templateId": 2})
    assert resp.status_code == 200
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["fileName"] == "Report A.pdf"
    assert base64.b64decode(results[0]["fileBase64"]) == b"%PDF-1.4 stub"


def test_generate_report_excludes_original_findings_report(client, stub, fake_soffice):
    stub.routes = {
        "GetReports": {"report": []},
    }
    call(client, "post", "/generateReport", {"projectId": 1, "templateId": 2})
    query = stub.queries_matching("GetReports")[0]["query"]
    assert '_neq: "Original Findings"' in query


def test_generate_report_uses_long_timeout(client, stub, fake_soffice):
    """Doc generation runs for minutes; it must not use the default query timeout."""
    stub.routes = {
        "GetReports": {"report": [{"id": 5, "title": "R"}]},
        "generateDocReport": {"generateDocReport": {
            "docBase64": base64.b64encode(b"x").decode(), "fileName": "R.docx",
        }},
    }
    call(client, "post", "/generateReport", {"projectId": 1, "templateId": 2})
    doc_call = stub.queries_matching("generateDocReport")[0]
    list_call = stub.queries_matching("GetReports")[0]
    assert doc_call["timeout"] > list_call["timeout"]


def test_generate_report_reports_per_report_errors(client, stub):
    stub.routes = {
        "GetReports": {"report": [{"id": 5, "title": "R"}]},
        "generateDocReport": FakeResponse(payload={"errors": [{"message": "template missing"}]}),
    }
    resp = call(client, "post", "/generateReport", {"projectId": 1, "templateId": 2})
    assert resp.status_code == 200
    assert resp.get_json()[0]["reportId"] == 5
    assert resp.get_json()[0]["error"]["message"] == "graphql error"


def test_generate_report_reports_conversion_failure(client, stub, monkeypatch):
    def boom(args, **kwargs):
        raise RuntimeError("soffice exploded")

    monkeypatch.setattr(app_module.subprocess, "run", boom)
    stub.routes = {
        "GetReports": {"report": [{"id": 5, "title": "R"}]},
        "generateDocReport": {"generateDocReport": {
            "docBase64": base64.b64encode(b"x").decode(), "fileName": "R.docx",
        }},
    }
    resp = call(client, "post", "/generateReport", {"projectId": 1, "templateId": 2})
    assert resp.status_code == 200
    assert resp.get_json()[0]["error"]["message"] == "PDF conversion failed"


# --- graphql_request transport ---------------------------------------------

def test_graphql_request_surfaces_transport_failure(client, monkeypatch):
    def boom(self, url, json=None, timeout=None, **kw):
        raise app_module.requests.RequestException("connection refused")

    monkeypatch.setattr(app_module.requests.Session, "post", boom)
    resp = call(client, "get", "/getClient?clientId=1")
    assert resp.status_code == 502
    assert resp.get_json()["error"]["message"] == "graphql request failed"


def test_graphql_request_surfaces_non_json_body(client, monkeypatch):
    monkeypatch.setattr(
        app_module.requests.Session, "post",
        lambda self, url, json=None, timeout=None, **kw: FakeResponse(status_code=200, payload=None),
    )
    resp = call(client, "get", "/getClient?clientId=1")
    assert resp.status_code == 502
    assert "decode failed" in resp.get_json()["error"]["message"]
