import base64
import os
import subprocess
import tempfile
from functools import wraps

import requests
import urllib3
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    def graphql_request(query, variables):
        try:
            response = session.post(
                graphql_url,
                json={"query": query, "variables": variables},
                timeout=30,
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

    return app


app = create_app()
