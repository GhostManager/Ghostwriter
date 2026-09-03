import base64
import json
import os
import re
import secrets
import subprocess
import tempfile
from functools import wraps
from urllib.parse import urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request


# Default friendly name used to locate the PoC source that has been uploaded as
# report evidence. The file itself is uploaded as .txt (".py" is not an allowed
# evidence extension) but the friendly name carries the script name, e.g.
# "poc.py". A manifest may override this with an explicit "attachment" key when a
# report holds more than one PoC.
POC_DEFAULT_ATTACHMENT_NAME = "poc.py"
# Sandbox resource limits are not part of the manifest, so fall back to these
# when the runtime block does not specify them.
POC_DEFAULT_MEM_MB = 256
POC_DEFAULT_CPU = 0.5


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_poc_manifest(raw):
    """
    Parse the ``poc`` extra field into a manifest dict.

    The field is a free-form multiline text field, so the manifest normally arrives
    as a JSON string. When it has been edited through a rich-text widget it may be
    wrapped in HTML (``<p>`` tags, ``&quot;`` entities); as a fallback the HTML is
    stripped before parsing. A native ``json`` extra field (already a dict) is
    passed through unchanged. Returns the manifest dict, or ``None`` if it cannot
    be parsed.
    """
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None

    candidates = [raw]
    stripped = BeautifulSoup(raw, "html.parser").get_text(separator="\n")
    if stripped != raw:
        candidates.append(stripped)

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def resolve_and_validate_inputs(params, provided):
    """
    Merge caller-supplied inputs over the manifest parameter defaults and validate
    each value against its parameter spec (enum membership, string pattern, type).

    Returns (resolved_inputs, error) where exactly one is non-None. ``resolved_inputs``
    contains every declared parameter (so downstream consumers such as credential
    templating and the runner ``inputs`` block are always complete).
    """
    provided = provided or {}
    if not isinstance(provided, dict):
        return None, {"error": "inputs must be an object"}

    resolved = {}
    param_names = set()
    for param in params or []:
        name = param.get("name")
        if not name:
            continue
        param_names.add(name)

        if name in provided and provided[name] is not None:
            value = provided[name]
        elif "default" in param:
            value = param.get("default")
        else:
            return None, {"error": f"missing required input: {name}"}

        ptype = param.get("type")
        if ptype == "enum":
            allowed = param.get("values") or []
            if value not in allowed:
                return None, {"error": f"input '{name}' must be one of {allowed}"}
        elif ptype == "string":
            if not isinstance(value, str):
                return None, {"error": f"input '{name}' must be a string"}
            pattern = param.get("pattern")
            if pattern and not re.fullmatch(pattern, value):
                return None, {"error": f"input '{name}' does not match required pattern"}
        elif ptype == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                return None, {"error": f"input '{name}' must be an integer"}
        elif ptype == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None, {"error": f"input '{name}' must be a number"}
        elif ptype == "boolean":
            if not isinstance(value, bool):
                return None, {"error": f"input '{name}' must be a boolean"}

        resolved[name] = value

    unknown = set(provided.keys()) - param_names
    if unknown:
        return None, {"error": f"unknown inputs: {sorted(unknown)}"}

    return resolved, None


def egress_allowlist_for(target_value):
    """Derive a ``host:port`` egress allowlist entry from a target URL."""
    if not isinstance(target_value, str):
        return []
    parsed = urlparse(target_value)
    host = parsed.hostname
    if not host:
        return []
    port = parsed.port
    if port is None:
        port = 80 if parsed.scheme == "http" else 443
    return [f"{host}:{port}"]


def build_runner_credentials(manifest_credentials, resolved_inputs):
    """
    Translate the manifest ``credentials`` block into the runner shape: drop the
    ``source`` key and expand ``{param}`` templates in string values (e.g. a
    ``ref`` of ``acme/poc/{test_account}`` becomes ``acme/poc/viewer-a``).

    Returns (credentials, error).
    """
    result = {}
    for key, entry in (manifest_credentials or {}).items():
        if not isinstance(entry, dict):
            result[key] = entry
            continue
        out = {}
        for field, value in entry.items():
            if field == "source":
                continue
            if isinstance(value, str):
                try:
                    value = value.format(**resolved_inputs)
                except (KeyError, IndexError, ValueError) as exc:
                    return None, {
                        "error": f"credential '{key}.{field}' references an unknown input",
                        "detail": str(exc),
                    }
            out[field] = value
        result[key] = out
    return result, None


def create_app():
    app = Flask(__name__)

    api_key = os.environ.get("FLASK_API_KEY", "")
    token = os.environ.get("GHOSTWRITER_API_TOKEN", "")
    graphql_url = os.environ.get("GHOSTWRITER_GRAPHQL_URL", "https://nginx/v1/graphql")

    if not api_key or not token or not graphql_url:
        raise RuntimeError(
            "FLASK_API_KEY, GHOSTWRITER_API_TOKEN, and GHOSTWRITER_GRAPHQL_URL must be set"
        )

    session = requests.Session()
    session.verify = False
    session.headers.update({"Authorization": f"Bearer {token}"})

    def require_api_key(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            provided = request.headers.get("X-API-Key", "")
            if not provided or provided != api_key:
                return jsonify({"error": "unauthorized"}), 401
            return fn(*args, **kwargs)

        return wrapper

    # Report generation Actions (generateDocReport) run for minutes; ordinary
    # queries should still fail fast.
    graphql_timeout = int(os.environ.get("GRAPHQL_TIMEOUT", "30"))
    graphql_report_timeout = int(os.environ.get("GRAPHQL_REPORT_TIMEOUT", "600"))

    # PoC runner configuration. These are optional so existing deployments that
    # do not use the runner still boot; /runPoc returns 503 until they are set.
    poc_runner_url = os.environ.get("POC_RUNNER_URL", "")
    poc_runner_api_key = os.environ.get("POC_RUNNER_API_KEY", "")
    poc_runner_timeout = int(os.environ.get("POC_RUNNER_TIMEOUT", "120"))
    poc_runner_verify_tls = os.environ.get("POC_RUNNER_VERIFY_TLS", "true").lower() not in (
        "0",
        "false",
        "no",
    )

    def graphql_request(query, variables, timeout=None):
        try:
            response = session.post(
                graphql_url,
                json={"query": query, "variables": variables},
                timeout=timeout or graphql_timeout,
            )
        except requests.RequestException as exc:
            return None, {"message": "graphql request failed", "detail": str(exc)}

        if response.status_code != 200:
            return None, {
                "message": "graphql request failed",
                "status": response.status_code,
                "body": response.text,
            }

        try:
            payload = response.json()
        except ValueError as exc:
            return None, {"message": "graphql response decode failed", "detail": str(exc)}

        if payload.get("errors"):
            return None, {"message": "graphql error", "errors": payload["errors"]}
        return payload.get("data"), None

    def parse_int(value, field_name):
        try:
            return int(value), None
        except (TypeError, ValueError):
            return None, {"error": f"{field_name} must be an integer"}

    @app.route("/createClient", methods=["POST"])
    @require_api_key
    def create_client():
        body = request.get_json(silent=True) or {}
        name = body.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400

        allowed_fields = {
            "name",
            "shortName",
            "codename",
            "description",
            "timezone",
            "address",
            "extraFields",
            "contacts",
            "logo_base64",
        }
        graphql_fields = allowed_fields - {"logo_base64"}
        client_input = {key: body[key] for key in graphql_fields if key in body}

        query = """
        mutation CreateClient($object: client_insert_input!) {
          insert_client_one(object: $object) {
            id
          }
        }
        """

        data, error = graphql_request(query, {"object": client_input})
        if error:
            return jsonify({"error": error}), 502

        client_id = data.get("insert_client_one", {}).get("id")
        if client_id is None:
            return jsonify({"error": "GraphQL did not return client id"}), 502

        return jsonify(data)

    @app.route("/updateClient", methods=["POST"])
    @require_api_key
    def update_client():
        body = request.get_json(silent=True) or {}
        client_id = body.get("clientId")
        if client_id is None:
            return jsonify({"error": "clientId is required"}), 400

        allowed_fields = {
            "name",
            "shortName",
            "codename",
            "description",
            "timezone",
            "address",
            "extraFields",
        }
        set_input = {key: body[key] for key in allowed_fields if key in body}

        if "extraFields" in set_input and isinstance(set_input["extraFields"], dict):
            set_input["extraFields"].pop("showResultsInDashboard", None)

        contacts = body.get("contacts")

        if not set_input and contacts is None:
            return jsonify({"error": "no fields to update"}), 400

        data = {}

        # Update scalar fields
        if set_input:
            query = """
            mutation UpdateClient($clientId: bigint!, $set: client_set_input!) {
              update_client_by_pk(pk_columns: {id: $clientId}, _set: $set) {
                id
                name
                shortName
              }
            }
            """
            data, error = graphql_request(query, {"clientId": int(client_id), "set": set_input})
            if error:
                return jsonify({"error": error}), 502

        if not data:
            data = {"update_client_by_pk": {"id": client_id}}

        return jsonify(data)

    @app.route("/uploadClientLogo", methods=["POST"])
    @require_api_key
    def upload_client_logo():
        """
        Upload a client logo. Expects JSON body: { "clientId": int, "fileBase64": str, "fileName": str }.
        Sets the logo for the client via the uploadClientLogo Hasura action.
        """
        body = request.get_json(silent=True) or {}
        client_id = body.get("clientId")
        file_base64 = body.get("fileBase64")
        file_name = body.get("fileName")
        if client_id is None:
            return jsonify({"error": "clientId is required"}), 400
        if file_base64 is None:
            return jsonify({"error": "fileBase64 is required"}), 400
        if file_name is None:
            return jsonify({"error": "fileName is required"}), 400

        client_id, err = parse_int(client_id, "clientId")
        if err:
            return jsonify({"error": err}), 400

        upload_mutation = """
        mutation UploadClientLogo($clientId: Int!, $file_base64: String!, $filename: String!) {
          uploadClientLogo(clientId: $clientId, file_base64: $file_base64, filename: $filename) {
            id
          }
        }
        """
        data, error = graphql_request(
            upload_mutation,
            {"clientId": client_id, "file_base64": file_base64, "filename": file_name},
        )
        if error:
            return jsonify({"error": error}), 502
        return jsonify(data)

    @app.route("/getClient", methods=["GET"])
    @require_api_key
    def get_client():
        body = request.get_json(silent=True) or {}
        client_id = request.args.get("clientId") or body.get("clientId")
        if client_id is None:
            return jsonify({"error": "clientId is required"}), 400
        client_id, error = parse_int(client_id, "clientId")
        if error:
            return jsonify(error), 400

        query = """
        query GetClient($clientId: bigint!) {
          client_by_pk(id: $clientId) {
            id
            name
            shortName
            codename
            description
            timezone
            address
            extraFields
          }
        }
        """

        data, error = graphql_request(query, {"clientId": client_id})
        if error:
            return jsonify({"error": error}), 502
        return jsonify(data)

    @app.route("/createProject", methods=["POST"])
    @require_api_key
    def create_project():
        body = request.get_json(silent=True) or {}
        required_fields = ["clientId", "projectTypeId", "startDate", "endDate"]
        missing = [field for field in required_fields if body.get(field) is None]
        if missing:
            return jsonify({"error": "missing required fields", "fields": missing}), 400

        allowed_fields = {
            "clientId",
            "projectTypeId",
            "codename",
            "description",
            "collab_note",
            "startDate",
            "endDate",
            "startTime",
            "endTime",
            "timezone",
            "slackChannel",
            "bloodhound_api_key_id",
            "bloodhound_api_key_token",
            "bloodhound_api_root_url",
            "scopes",
            "assignments",
            "reports",
        }
        project_input = {key: body[key] for key in allowed_fields if key in body}

        query = """
        mutation CreateProject($object: project_insert_input!) {
          insert_project_one(object: $object) {
            id
          }
        }
        """

        data, error = graphql_request(query, {"object": project_input})
        if error:
            return jsonify({"error": error}), 502
        return jsonify(data)

    @app.route("/updateProject", methods=["POST"])
    @require_api_key
    def update_project():
        body = request.get_json(silent=True) or {}
        project_id = body.get("projectId")
        if project_id is None:
            return jsonify({"error": "projectId is required"}), 400

        allowed_fields = {
            "clientId",
            "projectTypeId",
            "codename",
            "description",
            "collab_note",
            "startDate",
            "endDate",
            "startTime",
            "endTime",
            "timezone",
            "slackChannel",
            "bloodhound_api_key_id",
            "bloodhound_api_key_token",
            "bloodhound_api_root_url",
        }
        set_input = {key: body[key] for key in allowed_fields if key in body}

        if not set_input:
            return jsonify({"error": "no fields to update"}), 400

        query = """
        mutation UpdateProject($projectId: bigint!, $set: project_set_input!) {
          update_project_by_pk(pk_columns: {id: $projectId}, _set: $set) {
            id
          }
        }
        """

        data, error = graphql_request(query, {"projectId": int(project_id), "set": set_input})
        if error:
            return jsonify({"error": error}), 502
        return jsonify(data)

    @app.route("/getProjects", methods=["GET"])
    @require_api_key
    def get_projects():
        body = request.get_json(silent=True) or {}
        client_id = request.args.get("clientId") or body.get("clientId")
        if client_id is None:
            return jsonify({"error": "clientId is required"}), 400
        client_id, error = parse_int(client_id, "clientId")
        if error:
            return jsonify(error), 400

        query = """
        query ProjectsByClient($clientId: bigint!) {
          project(where: { clientId: { _eq: $clientId } }) {
            id
            codename
            description
            startDate
            endDate
            complete
            projectType {
              id
              projectType
            }
          }
        }
        """

        data, error = graphql_request(query, {"clientId": client_id})
        if error:
            return jsonify({"error": error}), 502
        return jsonify(data)

    @app.route("/getProject", methods=["GET"])
    @require_api_key
    def get_project():
        body = request.get_json(silent=True) or {}
        project_id = request.args.get("projectId") or body.get("projectId")
        if project_id is None:
            return jsonify({"error": "projectId is required"}), 400
        project_id, error = parse_int(project_id, "projectId")
        if error:
            return jsonify(error), 400

        query = """
        query GetProject($projectId: bigint!) {
          project_by_pk(id: $projectId) {
            id
            codename
            description
            startDate
            endDate
            startTime
            endTime
            complete
            timezone
            slackChannel
            collab_note
            extraFields
            clientId
            projectTypeId
            operatorId
            client {
              id
              name
              shortName
            }
            projectType {
              id
              projectType
            }
            reports(where: {title: {_neq: "Original Findings"}}) {
              id
              title
              projectId
              creation
              last_update
              archived
              complete
              delivered
              extraFields
              evidence {
                id
              }
              findings(order_by: {cvssScore: desc}) {
                id
                title
                description
                impact
                mitigation
                replication_steps
                references
                position
                complete
                affectedEntities
                cvssScore
                cvssVector
                findingGuidance
                extraFields
                severityId
                findingTypeId
                severity {
                  id
                  severity
                  weight
                }
                findingType {
                  id
                  findingType
                }
              }
            }
          }
        }
        """

        data, error = graphql_request(query, {"projectId": project_id})
        if error:
            return jsonify({"error": error}), 502

        download_query = """
        query DownloadEvidence($evidenceId: Int!) {
          downloadEvidence(evidenceId: $evidenceId) {
            evidenceId
            filename
            friendlyName
            fileBase64
          }
        }
        """

        project_data = data.get("project_by_pk")
        if project_data:
            for report in project_data.get("reports", []):
                evidence_list = report.get("evidence", [])
                downloaded = []
                for ev in evidence_list:
                    ev_data, ev_err = graphql_request(download_query, {"evidenceId": int(ev["id"])})
                    if ev_err:
                        downloaded.append({"evidenceId": ev["id"], "error": ev_err})
                    else:
                        downloaded.append(ev_data.get("downloadEvidence", {}))
                report["evidence"] = downloaded

        return jsonify(data)

    @app.route("/createRetest", methods=["POST"])
    @require_api_key
    def create_retest():
        body = request.get_json(silent=True) or {}
        project_id = body.get("projectId")
        if project_id is None:
            return jsonify({"error": "projectId is required"}), 400

        comments = body.get("comments") or []
        comments_by_finding = {}
        for c in comments:
            fid = c.get("findingId")
            if fid is not None:
                comments_by_finding.setdefault(int(fid), []).append(c)

        # 1. Fetch original project details and findings
        fetch_query = """
        query GetProjectForRetest($projectId: bigint!) {
          project_by_pk(id: $projectId) {
            id
            codename
            description
            clientId
            projectTypeId
            startDate
            endDate
            startTime
            endTime
            timezone
            slackChannel
            collab_note
            reports {
              findings {
                id
                title
                description
                impact
                mitigation
                replication_steps
                references
                position
                complete
                affectedEntities
                cvssScore
                cvssVector
                findingGuidance
                extraFields
                severityId
                findingTypeId
                hostDetectionTechniques
                networkDetectionTechniques
              }
            }
          }
        }
        """
        original, error = graphql_request(fetch_query, {"projectId": int(project_id)})
        if error:
            return jsonify({"error": error}), 502

        project = original.get("project_by_pk")
        if not project:
            return jsonify({"error": f"project {project_id} not found"}), 404

        # 2. Create new project with "Retest - [Original Name]"
        original_name = project.get("codename") or project.get("description") or f"Project {project_id}"
        new_project_input = {
            "clientId": project["clientId"],
            "projectTypeId": project["projectTypeId"],
            "codename": f"Retest - {original_name}",
            "description": project.get("description") or "",
            "startDate": project.get("startDate"),
            "endDate": project.get("endDate"),
            "startTime": project.get("startTime"),
            "endTime": project.get("endTime"),
            "timezone": project.get("timezone"),
            "slackChannel": project.get("slackChannel"),
            "collab_note": project.get("collab_note"),
            "bloodhound_api_key_id": "",
            "bloodhound_api_key_token": "",
            "bloodhound_api_root_url": "",
        }
        new_project_input = {k: v for k, v in new_project_input.items() if v is not None}

        create_project_query = """
        mutation CreateProject($object: project_insert_input!) {
          insert_project_one(object: $object) {
            id
          }
        }
        """
        proj_data, error = graphql_request(create_project_query, {"object": new_project_input})
        if error:
            return jsonify({"error": "failed to create retest project", "detail": error}), 502

        new_project_id = proj_data["insert_project_one"]["id"]

        # 3. Create report named "Original Findings" in the new project
        create_report_query = """
        mutation CreateReport($object: report_insert_input!) {
          insert_report_one(object: $object) {
            id
          }
        }
        """
        report_data, error = graphql_request(create_report_query, {
            "object": {
                "projectId": new_project_id,
                "title": "Original Findings",
                "creation": project.get("endDate"),
                "last_update": project.get("endDate"),
                "archived": False,
                "complete": False,
                "delivered": False,
                "include_bloodhound_data": False,
            }
        })
        if error:
            return jsonify({"error": "failed to create report", "detail": error}), 502

        new_report_id = report_data["insert_report_one"]["id"]

        # 4. Collect all findings from the original project's reports,
        #    tracking original IDs so we can map comments later
        all_findings = []
        original_ids = []
        finding_fields = [
            "title", "description", "impact", "mitigation",
            "replication_steps", "references", "position", "complete",
            "affectedEntities", "cvssScore", "cvssVector",
            "findingGuidance", "extraFields", "severityId", "findingTypeId",
            "hostDetectionTechniques", "networkDetectionTechniques",
        ]
        for report in project.get("reports", []):
            for finding in report.get("findings", []):
                original_finding_id = finding.get("id")
                new_finding = {k: finding[k] for k in finding_fields if k in finding and finding[k] is not None}

                # Apply comment data: prepend status to title, append description
                if original_finding_id is not None and int(original_finding_id) in comments_by_finding:
                    extra_text = ""
                    for comment in comments_by_finding[int(original_finding_id)]:
                        status = comment.get("status")
                        if status:
                            new_finding["title"] = f"{status} - {new_finding.get('title', '')}"
                        desc = comment.get("description", "")
                        if desc:
                            extra_text += f"\n\n<p><strong>Retest Comment:</strong></p>\n{desc}"
                    if extra_text:
                        new_finding["description"] = (new_finding.get("description") or "") + extra_text

                new_finding["reportId"] = new_report_id
                all_findings.append(new_finding)
                original_ids.append(original_finding_id)

        # 5. Insert findings into the new report, returning new IDs
        findings_count = 0
        old_to_new = {}
        if all_findings:
            insert_findings_query = """
            mutation InsertFindings($objects: [reportedFinding_insert_input!]!) {
              insert_reportedFinding(objects: $objects) {
                affected_rows
                returning {
                  id
                }
              }
            }
            """
            findings_data, error = graphql_request(insert_findings_query, {"objects": all_findings})
            if error:
                return jsonify({"error": "failed to insert findings", "detail": error}), 502
            findings_count = findings_data.get("insert_reportedFinding", {}).get("affected_rows", 0)

            returned = findings_data.get("insert_reportedFinding", {}).get("returning", [])
            for idx, row in enumerate(returned):
                if idx < len(original_ids) and original_ids[idx] is not None:
                    old_to_new[int(original_ids[idx])] = row["id"]

        # 6. Upload evidence from comments onto the new report (evidence is report-scoped)
        evidence_errors = []
        upload_evidence_query = """
        mutation UploadEvidence(
          $file_base64: String!,
          $filename: String!,
          $friendly_name: String!,
          $caption: String!,
          $description: String,
          $report: Int!
        ) {
          uploadEvidence(
            file_base64: $file_base64,
            filename: $filename,
            friendly_name: $friendly_name,
            caption: $caption,
            description: $description,
            report: $report
          ) {
            id
          }
        }
        """
        for comment in comments:
            original_fid = comment.get("findingId")
            evidence_b64 = comment.get("evidence_b64")
            if not evidence_b64 or original_fid is None:
                continue
            new_fid = old_to_new.get(int(original_fid))
            if new_fid is None:
                evidence_errors.append({
                    "originalFindingId": original_fid,
                    "error": "no matching new finding found",
                })
                continue

            _, err = graphql_request(upload_evidence_query, {
                "file_base64": evidence_b64,
                "filename": comment.get("evidence_filename", f"retest_evidence_{original_fid}.png"),
                "friendly_name": f"Retest Evidence - Finding {original_fid}",
                "caption": "Retest evidence",
                "description": comment.get("description", ""),
                "report": int(new_report_id),
            })
            if err:
                evidence_errors.append({
                    "originalFindingId": original_fid,
                    "newFindingId": new_fid,
                    "error": err,
                })

        result = {
            "originalProjectId": int(project_id),
            "newProjectId": new_project_id,
            "newReportId": new_report_id,
            "findingsCopied": findings_count,
            "findingIdMapping": old_to_new,
        }
        if evidence_errors:
            result["evidenceErrors"] = evidence_errors

        return jsonify(result)

    @app.route("/getStatistics", methods=["GET"])
    @require_api_key
    def get_statistics():
        body = request.get_json(silent=True) or {}
        client_id = request.args.get("clientId") or body.get("clientId")
        if client_id is None:
            return jsonify({"error": "clientId is required"}), 400
        client_id, error = parse_int(client_id, "clientId")
        if error:
            return jsonify(error), 400

        # Query 1: Total findings for client grouped by severity
        query_client_totals = """
        query ClientSeverityTotals($clientId: bigint!) {
          findingSeverity(order_by: { weight: asc }) {
            id
            severity
            reportedFindings_aggregate(
              where: {
                report: {
                  project: {
                    clientId: { _eq: $clientId }
                    client: {
                      extraFields: { _contains: { showResultsInDashboard: true } }
                    }
                  }
                }
              }
            ) {
              aggregate {
                count
              }
            }
          }
        }
        """

        # Query 2: Projects with their findings (for per-project severity counts)
        query_projects_findings = """
        query ProjectsFindingsByClient($clientId: bigint!) {
          project(
            where: {
              clientId: { _eq: $clientId }
              client: { extraFields: { _contains: { showResultsInDashboard: true } } }
            }
          ) {
            id
            codename
            reports {
              findings {
                severityId
                severity {
                  id
                  severity
                }
              }
            }
          }
        }
        """

        data1, error = graphql_request(query_client_totals, {"clientId": client_id})
        if error:
            return jsonify({"error": error}), 502

        data2, error = graphql_request(query_projects_findings, {"clientId": client_id})
        if error:
            return jsonify({"error": error}), 502

        # Build client totals
        client_totals = []
        for item in data1.get("findingSeverity", []):
            count = item["reportedFindings_aggregate"]["aggregate"]["count"]
            client_totals.append({
                "severityId": item["id"],
                "severity": item["severity"],
                "count": count,
            })

        # Build per-project totals
        projects = []
        for proj in data2.get("project", []):
            severity_counts = {}
            for report in proj.get("reports", []):
                for finding in report.get("findings", []):
                    sev = finding.get("severity")
                    if sev:
                        sid = sev.get("id")
                        sname = sev.get("severity", "")
                        key = (sid, sname)
                        severity_counts[key] = severity_counts.get(key, 0) + 1

            severity_totals = [
                {"severityId": sid, "severity": sname, "count": c}
                for (sid, sname), c in sorted(severity_counts.items(), key=lambda x: (x[0][0] or 0))
            ]

            projects.append({
                "id": proj["id"],
                "codename": proj.get("codename"),
                "severityTotals": severity_totals,
            })

        return jsonify({
            "clientTotals": client_totals,
            "projects": projects,
        })

    def docx_base64_to_pdf_base64(docx_base64, original_filename):
        """
        Convert DOCX base64 to PDF base64 using LibreOffice headless.
        Returns (pdf_base64, pdf_filename) or raises on failure.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "report.docx")
            with open(docx_path, "wb") as f:
                f.write(base64.b64decode(docx_base64))
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmpdir,
                    docx_path,
                ],
                capture_output=True,
                timeout=120,
                cwd=tmpdir,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed: {result.stderr.decode('utf-8', errors='replace')}"
                )
            base_name = os.path.splitext(original_filename)[0] if original_filename else "report"
            pdf_path = os.path.join(tmpdir, "report.pdf")
            if not os.path.isfile(pdf_path):
                raise RuntimeError("LibreOffice did not produce report.pdf")
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_filename = f"{base_name}.pdf"
            return base64.b64encode(pdf_bytes).decode("utf-8"), pdf_filename

    @app.route("/generateReport", methods=["POST"])
    @require_api_key
    def generate_report():
        """
        Generate PDF reports for all reports in a project (excluding "Original Findings").
        DOCX is generated then converted to PDF. Expects JSON body: { "projectId": int, "templateId": int }.
        Returns [{ "fileName": str, "fileBase64": str }, ...] (PDF).
        """
        body = request.get_json(silent=True) or {}
        project_id = body.get("projectId")
        template_id = body.get("templateId")
        if project_id is None:
            return jsonify({"error": "projectId is required"}), 400
        if template_id is None:
            return jsonify({"error": "templateId is required"}), 400

        project_id, err = parse_int(project_id, "projectId")
        if err:
            return jsonify({"error": err}), 400
        template_id, err = parse_int(template_id, "templateId")
        if err:
            return jsonify({"error": err}), 400

        reports_query = """
        query GetReports($projectId: bigint!) {
          report(
            where: {
              projectId: { _eq: $projectId }
              title: { _neq: "Original Findings" }
            }
          ) {
            id
            title
          }
        }
        """
        data, error = graphql_request(reports_query, {"projectId": project_id})
        if error:
            return jsonify({"error": error}), 502

        reports = data.get("report", [])
        if not reports:
            return jsonify([])

        generate_doc_mutation = """
        mutation GenerateDocReport($id: Int!, $templateId: Int!) {
          generateDocReport(id: $id, templateId: $templateId) {
            docBase64
            fileName
          }
        }
        """
        results = []
        for report in reports:
            report_id = report["id"]
            doc_data, doc_error = graphql_request(
                generate_doc_mutation,
                {"id": report_id, "templateId": template_id},
                timeout=graphql_report_timeout,
            )
            if doc_error:
                results.append({
                    "reportId": report_id,
                    "error": doc_error,
                })
                continue
            payload = doc_data.get("generateDocReport")
            if not payload:
                results.append({"reportId": report_id, "error": {"message": "empty response"}})
                continue
            docx_base64 = payload.get("docBase64", "")
            original_filename = payload.get("fileName", "")
            try:
                pdf_base64, pdf_filename = docx_base64_to_pdf_base64(docx_base64, original_filename)
            except Exception as e:
                results.append({
                    "reportId": report_id,
                    "error": {"message": "PDF conversion failed", "detail": str(e)},
                })
                continue
            results.append({
                "fileName": pdf_filename,
                "fileBase64": pdf_base64,
            })

        return jsonify(results)

    @app.route("/runPoc", methods=["POST"])
    @require_api_key
    def run_poc():
        """
        Run a finding's proof-of-concept in the external sandbox runner.

        Request body:
            {
              "finding_id": 4127,
              "poc_version": 1,
              "inputs": { "target": "...", "object_id": "8814" },
              "client_run_id": "b3f1c2a4-..."
            }

        The endpoint fetches the finding's ``poc`` manifest (a JSON extra field on
        ``reportedFinding``), verifies the requested ``poc_version`` and validates the
        supplied inputs against the manifest parameters, then downloads the PoC source
        (uploaded as report evidence under the friendly name ``poc.py`` or the manifest's
        ``attachment`` override). On success it forwards a run request to the
        runner and returns the runner's response synchronously.
        """
        if not poc_runner_url:
            return jsonify({"error": "poc runner is not configured"}), 503

        body = request.get_json(silent=True) or {}
        finding_id = body.get("finding_id")
        poc_version = body.get("poc_version")
        client_run_id = body.get("client_run_id")
        provided_inputs = body.get("inputs") or {}

        if finding_id is None:
            return jsonify({"error": "finding_id is required"}), 400
        if poc_version is None:
            return jsonify({"error": "poc_version is required"}), 400
        if not client_run_id:
            return jsonify({"error": "client_run_id is required"}), 400

        finding_id, err = parse_int(finding_id, "finding_id")
        if err:
            return jsonify(err), 400

        # 1. Fetch the finding and its PoC manifest
        finding_query = """
        query GetFindingPoc($id: bigint!) {
          reportedFinding_by_pk(id: $id) {
            id
            title
            reportId
            extraFields
          }
        }
        """
        data, error = graphql_request(finding_query, {"id": finding_id})
        if error:
            return jsonify({"error": error}), 502

        finding = (data or {}).get("reportedFinding_by_pk")
        if not finding:
            return jsonify({"error": f"finding {finding_id} not found"}), 404

        extra_fields = finding.get("extraFields") or {}
        manifest = parse_poc_manifest(extra_fields.get("poc"))
        if manifest is None:
            return jsonify({"error": f"finding {finding_id} has no valid PoC manifest"}), 404

        # 2. Verify the manifest against the request
        manifest_finding_id = manifest.get("finding_id")
        if manifest_finding_id is not None and int(manifest_finding_id) != finding_id:
            return jsonify({
                "error": "manifest finding_id does not match finding",
                "manifestFindingId": manifest_finding_id,
                "findingId": finding_id,
            }), 409
        if manifest.get("poc_version") != poc_version:
            return jsonify({
                "error": "poc_version mismatch",
                "requested": poc_version,
                "available": manifest.get("poc_version"),
            }), 409
        if not manifest.get("runnable", False):
            return jsonify({"error": "PoC is not marked runnable"}), 409

        # 3. Resolve and validate inputs against the manifest parameters
        resolved_inputs, error = resolve_and_validate_inputs(manifest.get("params"), provided_inputs)
        if error:
            return jsonify(error), 400

        targets_from = manifest.get("targets_from")
        target_value = resolved_inputs.get(targets_from) if targets_from else None
        egress_allowlist = egress_allowlist_for(target_value)

        credentials, error = build_runner_credentials(manifest.get("credentials"), resolved_inputs)
        if error:
            return jsonify(error), 400

        # 4. Locate and download the PoC source (uploaded as report evidence)
        report_id = finding.get("reportId")
        if report_id is None:
            return jsonify({"error": f"finding {finding_id} is not attached to a report"}), 409

        friendly_name = manifest.get("attachment") or POC_DEFAULT_ATTACHMENT_NAME
        evidence_query = """
        query GetPocEvidence($reportId: bigint!, $friendlyName: String!) {
          evidence(where: {reportId: {_eq: $reportId}, friendlyName: {_eq: $friendlyName}}) {
            id
            friendlyName
            document
          }
        }
        """
        ev_data, error = graphql_request(
            evidence_query, {"reportId": int(report_id), "friendlyName": friendly_name}
        )
        if error:
            return jsonify({"error": error}), 502

        evidence_list = (ev_data or {}).get("evidence") or []
        if not evidence_list:
            return jsonify({
                "error": "PoC source evidence not found",
                "friendlyName": friendly_name,
                "reportId": report_id,
            }), 404

        download_query = """
        query DownloadEvidence($evidenceId: Int!) {
          downloadEvidence(evidenceId: $evidenceId) {
            evidenceId
            filename
            friendlyName
            fileBase64
          }
        }
        """
        dl_data, error = graphql_request(download_query, {"evidenceId": int(evidence_list[0]["id"])})
        if error:
            return jsonify({"error": error}), 502

        downloaded = (dl_data or {}).get("downloadEvidence") or {}
        file_base64 = downloaded.get("fileBase64")
        if not file_base64:
            return jsonify({"error": "PoC source evidence has no content"}), 502
        try:
            poc_source = base64.b64decode(file_base64).decode("utf-8", errors="replace")
        except (ValueError, TypeError) as exc:
            return jsonify({"error": "failed to decode PoC source", "detail": str(exc)}), 502

        # 5. Assemble the runner request
        runtime = manifest.get("runtime") or {}
        limits = {
            "timeout_seconds": runtime.get("timeout_seconds", 60),
            "max_requests": runtime.get("max_requests", 5),
            "mem_mb": runtime.get("mem_mb", POC_DEFAULT_MEM_MB),
            "cpu": runtime.get("cpu", POC_DEFAULT_CPU),
        }
        runner_body = {
            "job_ref": f"run-{finding_id}-{str(client_run_id).split('-')[0]}",
            "poc_source": poc_source,
            "entrypoint": runtime.get("entrypoint", ["python", "/poc/poc.py"]),
            "image": runtime.get("image"),
            "inputs": resolved_inputs,
            "egress_allowlist": egress_allowlist,
            "run_token": f"rtok_{secrets.token_hex(24)}",
            "credentials": credentials,
            "limits": limits,
        }

        # 6. Forward to the runner and return its response synchronously
        runner_headers = {"Content-Type": "application/json"}
        if poc_runner_api_key:
            runner_headers["X-API-Key"] = poc_runner_api_key
        # The HTTP timeout must outlast the sandbox job timeout so the runner has
        # time to respond after the PoC itself hits its limit.
        http_timeout = max(poc_runner_timeout, limits["timeout_seconds"] + 15)

        try:
            runner_resp = requests.post(
                poc_runner_url,
                json=runner_body,
                headers=runner_headers,
                timeout=http_timeout,
                verify=poc_runner_verify_tls,
            )
        except requests.RequestException as exc:
            return jsonify({"error": "poc runner request failed", "detail": str(exc)}), 502

        try:
            runner_json = runner_resp.json()
        except ValueError:
            return jsonify({
                "error": "poc runner returned a non-JSON response",
                "status": runner_resp.status_code,
                "body": runner_resp.text,
            }), 502

        return jsonify(runner_json), runner_resp.status_code

    return app


app = create_app()
