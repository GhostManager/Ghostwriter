"""
Tests for the middleware ``/runPoc`` PoC-runner endpoint.

These are standalone (the middleware is not part of the Django test suite). Run
from this directory with the middleware dependencies installed:

    pip install flask requests beautifulsoup4 pytest
    pytest test_app.py
"""
import base64
import json
import os

import pytest


# create_app() reads these at construction time, so set them before importing.
os.environ.setdefault("FLASK_API_KEY", "test-key")
os.environ.setdefault("GHOSTWRITER_API_TOKEN", "test-token")
os.environ.setdefault("GHOSTWRITER_GRAPHQL_URL", "https://ghostwriter.test/v1/graphql")
os.environ.setdefault("POC_RUNNER_URL", "https://runner.test/run")
os.environ.setdefault("POC_RUNNER_API_KEY", "runner-key")

import app as app_module  # noqa: E402


MANIFEST = {
    "manifest_version": 1,
    "poc_version": 1,
    "finding_id": 4127,
    "title": "BOLA: order records readable across tenants",
    "cwe": 639,
    "runnable": True,
    "mutates": False,
    "restore": None,
    "params": [
        {
            "name": "target",
            "type": "enum",
            "values": ["https://api.acme-staging.com", "https://api.acme.com"],
            "default": "https://api.acme-staging.com",
        },
        {
            "name": "test_account",
            "type": "enum",
            "values": ["viewer-a", "viewer-b"],
            "default": "viewer-a",
        },
        {
            "name": "object_id",
            "type": "string",
            "pattern": "^[0-9]{1,10}$",
            "default": "8814",
        },
    ],
    "targets_from": "target",
    "credentials": {
        "test_account": {"source": "vault", "ref": "acme/poc/{test_account}"},
    },
    "runtime": {
        "image": "poc-runner:v1",
        "entrypoint": ["python", "/poc/poc.py"],
        "timeout_seconds": 60,
        "max_requests": 5,
    },
}

POC_SOURCE = "print('hello from poc')\n"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def make_graphql_handler(finding=None, evidence=None, poc_source=POC_SOURCE):
    """Return a fake ``session.post`` that answers the three GraphQL queries."""

    def handler(url, json=None, timeout=None, **kwargs):
        query = (json or {}).get("query", "")
        if "reportedFinding_by_pk" in query:
            return FakeResponse(payload={"data": {"reportedFinding_by_pk": finding}})
        if "evidence(where" in query:
            return FakeResponse(payload={"data": {"evidence": evidence}})
        if "downloadEvidence" in query:
            b64 = base64.b64encode(poc_source.encode()).decode()
            return FakeResponse(payload={"data": {"downloadEvidence": {"fileBase64": b64}}})
        raise AssertionError(f"unexpected graphql query: {query[:60]}")

    return handler


@pytest.fixture
def client(monkeypatch):
    app = app_module.create_app()
    app.testing = True
    return app.test_client()


def _finding(manifest=MANIFEST, report_id=99):
    # The ``poc`` extra field is a multiline text field, so the manifest is stored
    # as a JSON string. Tests may pass a pre-serialized string (e.g. HTML-wrapped).
    poc = manifest if isinstance(manifest, str) else json.dumps(manifest)
    return {"id": 4127, "title": "t", "reportId": report_id, "extraFields": {"poc": poc}}


def _post(client, body):
    return client.post("/runPoc", json=body, headers={"X-API-Key": "test-key"})


# --- Pure helpers -----------------------------------------------------------

def test_parse_manifest_from_plain_json_string():
    assert app_module.parse_poc_manifest(json.dumps(MANIFEST)) == MANIFEST


def test_parse_manifest_from_dict():
    assert app_module.parse_poc_manifest(MANIFEST) == MANIFEST


def test_parse_manifest_from_rich_text_html():
    # A rich-text widget may wrap the JSON in <p> tags and HTML-encode quotes.
    raw = json.dumps({"poc_version": 1, "runnable": True})
    html = "<p>" + raw.replace('"', "&quot;") + "</p>"
    assert app_module.parse_poc_manifest(html) == {"poc_version": 1, "runnable": True}


def test_parse_manifest_invalid_returns_none():
    assert app_module.parse_poc_manifest("not json") is None
    assert app_module.parse_poc_manifest(None) is None
    assert app_module.parse_poc_manifest("[1, 2, 3]") is None  # not an object


def test_resolve_inputs_applies_defaults():
    resolved, err = app_module.resolve_and_validate_inputs(
        MANIFEST["params"], {"object_id": "8814"}
    )
    assert err is None
    assert resolved == {
        "target": "https://api.acme-staging.com",
        "test_account": "viewer-a",
        "object_id": "8814",
    }


def test_resolve_inputs_rejects_bad_pattern():
    _, err = app_module.resolve_and_validate_inputs(MANIFEST["params"], {"object_id": "abc"})
    assert err and "pattern" in err["error"]


def test_resolve_inputs_rejects_bad_enum():
    _, err = app_module.resolve_and_validate_inputs(MANIFEST["params"], {"target": "https://evil"})
    assert err and "must be one of" in err["error"]


def test_resolve_inputs_rejects_unknown_key():
    _, err = app_module.resolve_and_validate_inputs(MANIFEST["params"], {"nope": 1})
    assert err and "unknown inputs" in err["error"]


def test_egress_allowlist():
    assert app_module.egress_allowlist_for("https://api.acme-staging.com") == [
        "api.acme-staging.com:443"
    ]
    assert app_module.egress_allowlist_for("http://x.test:8080/y") == ["x.test:8080"]
    assert app_module.egress_allowlist_for("not-a-url") == []


def test_build_credentials_expands_template():
    creds, err = app_module.build_runner_credentials(
        MANIFEST["credentials"], {"test_account": "viewer-b"}
    )
    assert err is None
    assert creds == {"test_account": {"ref": "acme/poc/viewer-b"}}


# --- Endpoint ---------------------------------------------------------------

def test_run_poc_happy_path(client, monkeypatch):
    monkeypatch.setattr(
        app_module.requests.Session,
        "post",
        lambda self, url, json=None, timeout=None, **kw: make_graphql_handler(
            finding=_finding(), evidence=[{"id": 5, "friendlyName": "poc.py", "document": "poc-4127.txt"}]
        )(url, json=json, timeout=timeout),
    )

    captured = {}

    def fake_runner_post(url, json=None, headers=None, timeout=None, verify=None):
        captured["url"] = url
        captured["body"] = json
        captured["headers"] = headers
        return FakeResponse(payload={"status": "done", "signal": "cross_tenant_record_returned"})

    monkeypatch.setattr(app_module.requests, "post", fake_runner_post)

    resp = _post(client, {
        "finding_id": 4127,
        "poc_version": 1,
        "inputs": {"target": "https://api.acme-staging.com", "object_id": "8814"},
        "client_run_id": "b3f1c2a4-dead-beef",
    })

    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["signal"] == "cross_tenant_record_returned"

    body = captured["body"]
    assert body["job_ref"] == "run-4127-b3f1c2a4"
    assert body["image"] == "poc-runner:v1"
    assert body["poc_source"] == POC_SOURCE
    assert body["inputs"] == {
        "target": "https://api.acme-staging.com",
        "test_account": "viewer-a",
        "object_id": "8814",
    }
    assert body["egress_allowlist"] == ["api.acme-staging.com:443"]
    assert body["credentials"] == {"test_account": {"ref": "acme/poc/viewer-a"}}
    assert body["run_token"].startswith("rtok_")
    assert body["limits"]["timeout_seconds"] == 60
    assert captured["headers"]["X-API-Key"] == "runner-key"


def test_run_poc_version_mismatch(client, monkeypatch):
    monkeypatch.setattr(
        app_module.requests.Session,
        "post",
        lambda self, url, json=None, timeout=None, **kw: make_graphql_handler(finding=_finding())(
            url, json=json, timeout=timeout
        ),
    )
    resp = _post(client, {"finding_id": 4127, "poc_version": 2, "client_run_id": "r1"})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "poc_version mismatch"


def test_run_poc_missing_manifest(client, monkeypatch):
    finding = {"id": 4127, "reportId": 99, "extraFields": {}}
    monkeypatch.setattr(
        app_module.requests.Session,
        "post",
        lambda self, url, json=None, timeout=None, **kw: make_graphql_handler(finding=finding)(
            url, json=json, timeout=timeout
        ),
    )
    resp = _post(client, {"finding_id": 4127, "poc_version": 1, "client_run_id": "r1"})
    assert resp.status_code == 404
    assert "no valid PoC manifest" in resp.get_json()["error"]


def test_run_poc_evidence_not_found(client, monkeypatch):
    monkeypatch.setattr(
        app_module.requests.Session,
        "post",
        lambda self, url, json=None, timeout=None, **kw: make_graphql_handler(
            finding=_finding(), evidence=[]
        )(url, json=json, timeout=timeout),
    )
    resp = _post(client, {"finding_id": 4127, "poc_version": 1, "client_run_id": "r1"})
    assert resp.status_code == 404
    assert "evidence not found" in resp.get_json()["error"]


def test_run_poc_requires_api_key(client):
    resp = client.post("/runPoc", json={"finding_id": 1, "poc_version": 1, "client_run_id": "r"})
    assert resp.status_code == 401


def test_run_poc_runner_not_configured(monkeypatch):
    monkeypatch.delenv("POC_RUNNER_URL", raising=False)
    app = app_module.create_app()
    app.testing = True
    c = app.test_client()
    resp = c.post(
        "/runPoc",
        json={"finding_id": 1, "poc_version": 1, "client_run_id": "r"},
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 503
