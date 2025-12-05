# Only export main API classes and exceptions
__all__ = [
    "Credentials",
    "APIVersion",
    "Domain",
    "ErrorDetails",
    "ErrorResponse",
    "APIException",
    "APIClient",
]
# Standard Libraries
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Counter, Literal, Optional, NamedTuple, Dict, Any, List

# Django Imports
from django.conf import settings

# 3rd Party Libraries
import requests
from markdown import markdown

logger = logging.getLogger(__name__)


class Credentials(NamedTuple):
    token_id: str
    token_key: str

class APIVersion(NamedTuple):
    current_api_version: str
    deprecated_api_version: str
    server_version: str
    edition: Literal["community", "enterprise"] | None


class Domain(NamedTuple):
    name: str
    sid: str
    collected: bool

class ErrorDetails(NamedTuple):
    context: str
    message: str

    @classmethod
    def from_json_dict(cls, json_dict: Dict[str, Any]) -> "ErrorDetails":
        return ErrorDetails(
            context=json_dict["context"],
            message=json_dict["message"],
        )

class ErrorResponse(NamedTuple):
    status: int | None
    timestamp: str
    request_id: str
    errors: List[ErrorDetails]

    @classmethod
    def from_json_dict(cls, json_dict: Dict[str, Any]) -> "ErrorResponse":
        errors: List[ErrorDetails] = []

        for error_details_json in json_dict["errors"]:
            errors.append(ErrorDetails.from_json_dict(error_details_json))

        return ErrorResponse(
            status=json_dict.get("status"),
            timestamp=json_dict["timestamp"],
            request_id=json_dict["request_id"],
            errors=errors,
        )

class APIException(Exception):
    def __init__(self, msg: str, err_response: ErrorResponse | str | None = None, http_code: int | None = None) -> None:
        message = msg
        if err_response is not None:
            message += " " + repr(err_response)
        super().__init__(message)

        self.msg = msg
        self.err_response = err_response
        self.http_code = http_code


class APIClient:
    def __init__(self, scheme: str, host: str, port: int | None, credentials: Credentials) -> None:
        self._scheme = scheme
        self._host = host
        self._port = port if port is not None else (443 if scheme == "https" else 80)
        self._credentials = credentials

    def _format_url(self, uri: str) -> str:
        formatted_uri = uri
        if uri.startswith("/"):
            formatted_uri = formatted_uri[1:]

        return f"{self._scheme}://{self._host}:{self._port}/{formatted_uri}"

    def _request(self, method: str, uri: str, body: Optional[bytes] = None) -> requests.Response:
        digester = hmac.new(self._credentials.token_key.encode(), None, hashlib.sha256)
        digester.update(f"{method}{uri}".encode())

        # Update the digester for further chaining
        digester = hmac.new(digester.digest(), None, hashlib.sha256)

        datetime_formatted = datetime.now().astimezone().isoformat("T")
        digester.update(datetime_formatted[:13].encode())

        # Update the digester for further chaining
        digester = hmac.new(digester.digest(), None, hashlib.sha256)

        # If there is no body content, the HMAC digest is computed anyway, simply with no values written to the
        # digester.
        if body is not None:
            digester.update(body)

        # Perform the request with the signed and expected headers
        url = self._format_url(uri)
        logger.info("BH API: %s %s", method, url)
        response = requests.request(
            method=method,
            url=self._format_url(uri),
            headers={
                "User-Agent": f"Ghostwriter {settings.VERSION}",
                "Authorization": f"bhesignature {self._credentials.token_id}",
                "RequestDate": datetime_formatted,
                "Signature": base64.b64encode(digester.digest()),
                "Content-Type": "application/json",
            },
            data=body,
            timeout=(3, 10),
        )

        if response.status_code < 200:
            raise APIException(
                msg=f"API response received with unexpected status code {response.status_code}",
                http_code=response.status_code,
            )

        if response.status_code >= 400:
            # Attempt to read an error response object from the API response
            if response.headers["Content-type"] == "application/json":
                err_response = ErrorResponse.from_json_dict(response.json())
            else:
                err_response = response.text
            raise APIException(
                msg=f"API request failed with status code {response.status_code}",
                err_response=err_response,
                http_code=response.status_code,
            )

        return response

    def get_version(self) -> APIVersion:
        response = self._request("GET", "/api/version")
        payload = response.json()["data"]

        return APIVersion(
            current_api_version=payload["API"]["current_version"],
            deprecated_api_version=payload["API"]["deprecated_version"],
            server_version=payload["server_version"],
            edition=payload.get("product_edition"),
        )

    def get_domains(self) -> list[Domain]:
        response = self._request("GET", "/api/v1/availabledomains")
        payload = response.json()

        domains = []
        for domain in payload:
            domains.append(Domain(domain["name"], domain["id"], domain["collected"]))

        return domains

    def get_all(self) -> dict:
        findings = self.get_enterprise_findings()
        domains = self.get_community_domains()
        return {
            "findings": findings,
            "domains": domains,
        }

    def get_enterprise_findings(self) -> dict:
        """
        Gets findings from BHEE
        """
        def _calculate_severity(finding: dict) -> str:
            """
            Calculate severity based on ``impact_percentage`` or ``exposure_percentage``.

            Use ``impact_percentage`` unless the finding is a relationship type (has a source). This could mean a
            finding with a 99% impact (Critical) is marked as Low because its exposure is only 1%. This means the
            finding could lead to a Critical impact, but only 1% of principals has a path. We assume Tier 0 is always
            critical, so we use exposure in these cases to help prioritize.

            The exception to this rule is if ``LargeDefaultGroups`` is in the ``finding_name``, then we use
            ``impact_percentage`` ``LargeDefaultGroups`` means exposure is 100% so impact is more relevant for
            prioritizing the finding.
            """
            impact_percentage = finding.get("impact_percentage", 0)
            exposure_percentage = finding.get("exposure_percentage", 0)
            if finding.get("sourceid") is not None and "LargeDefaultGroups" not in finding.get("finding_name", ""):
                impact_percentage = exposure_percentage
            # Convert to percentage (0.98473 -> 98.473) for comparison
            impact_pct = impact_percentage * 100
            if impact_pct >= 95:
                return "Critical"
            elif impact_pct >= 80:
                return "High"
            elif impact_pct >= 40:
                return "Moderate"
            else:
                return "Low"

        def _build_target_entry(finding: dict, severity: str) -> dict:
            """
            Build a target entry dictionary from a finding with calculated severity.
            """
            return {
                # There is always a target, but source is only present for relationship findings
                # Exposure values are linked to the source-target relationship
                "target_id": finding.get("target_id"),
                "target_kind": finding.get("target_kind", None),
                "target_properties": finding.get("target_properties", {}),

                "impact_count": finding.get("impact_count", 0),
                "impact_percentage": finding.get("impact_percentage", 0),

                # BHE's API has a typo in "sourceid" (missing underscore)
                "source_id": finding.get("sourceid", None),
                "source_kind": finding.get("source_kind", None),
                "source_properties": finding.get("source_properties", {}),

                "exposure_count": finding.get("exposure_count", 0),
                "exposure_percentage": finding.get("exposure_percentage", 0),

                "attack_path_edge_id": finding.get("attack_path_edge_id", None),

                "severity": severity,
            }

        try:
            response = self._request("GET", "/api/v2/attack-paths/details")
        except APIException as err:
            if err.http_code == 404:
                return None
            raise
        payload = response.json()["data"]
        grouped = {}

        # Some finding assets have different fields for "tier zero" (tz) targets, so build
        # two dicts - one for tz and one for others (tx).
        tzassets = {}
        txassets = {}
        for assetKey, asset in payload["finding_assets"].items():
            tzfields = {}
            txfields = {}
            for term in ["title", "type", "references", "short_description", "long_description", "short_remediation", "long_remediation"]:
                tzkey = term + ".md"
                txkey = "tx-" + tzkey
                tzvalue = asset[tzkey]
                txvalue = asset.get(txkey, tzvalue)
                tzvalue = base64.b64decode(tzvalue).decode("utf-8")
                txvalue = base64.b64decode(txvalue).decode("utf-8")
                if term in ("title", "type"):
                    tzvalue = tzvalue.strip()
                    txvalue = txvalue.strip()
                else:
                    tzvalue = markdown(tzvalue)
                    txvalue = markdown(txvalue)
                tzfields[term] = tzvalue
                txfields[term] = txvalue
            tzassets[assetKey] = tzfields
            txassets[assetKey] = txfields

        # Find the group name for tier zero targets
        features = self.get_features()
        if features.get("tier_management_engine"):
            tzgroup = self._get_tier_zero_group()
        else:
            tzgroup = None

        # Add assets to each finding based on name and tier
        findings = payload["findings"]
        for finding in findings:
            if tzgroup is not None and finding.get("asset_group") == tzgroup and finding["finding_name"] in txassets:
                finding["assets"] = txassets[finding["finding_name"]]
            else:
                finding["assets"] = tzassets.get(finding["finding_name"])

            finding_name = finding.get("finding_name")
            environment_id = finding.get("environment_id")
            if not finding_name:
                continue

            # Create unique key from ``finding_name`` and ``environment_id``
            unique_key = (finding_name, environment_id)

            if unique_key not in grouped:
                # First occurrence - create entry with all fields
                grouped[unique_key] = dict(finding)
                # Move ``finding_name`` to the top level of the dict
                grouped[unique_key] = {"finding_name": finding.pop("finding_name"), **grouped[unique_key]}

                # Calculate severity and build target entry
                severity = _calculate_severity(finding)
                grouped[unique_key]["principals"] = [_build_target_entry(finding, severity)]

                # Drop values from top level that are part of the unique target/source combinations
                grouped[unique_key].pop("target_id", None)
                grouped[unique_key].pop("target_kind", None)
                grouped[unique_key].pop("target_properties", None)

                grouped[unique_key].pop("impact_count", None)
                grouped[unique_key].pop("impact_percentage", None)

                grouped[unique_key].pop("sourceid", None)
                grouped[unique_key].pop("source_kind", None)
                grouped[unique_key].pop("source_properties", None)

                grouped[unique_key].pop("exposure_count", None)
                grouped[unique_key].pop("exposure_percentage", None)

                grouped[unique_key].pop("attack_path_edge_id", None)
            else:
                # Additional finding occurrence - just add the target information if not already present
                target_id = finding.get("target_id")
                # Check if this ``target_id`` is already in the list
                existing_target_ids = [t["target_id"] for t in grouped[unique_key]["principals"]]
                if target_id not in existing_target_ids:
                    severity = _calculate_severity(finding)
                    grouped[unique_key]["principals"].append(_build_target_entry(finding, severity))

        # Now we set the ``severity`` at the top level based on the highest severity of its target(s)
        severity_order = {
            "Low": 1,
            "Moderate": 2,
            "High": 3,
            "Critical": 4,
        }
        for finding_key, finding_value in grouped.items():
            highest_severity = "Low"
            for target in finding_value["principals"]:
                target_severity = target.get("severity", "Low")
                if severity_order.get(target_severity, 0) > severity_order.get(highest_severity, 0):
                    highest_severity = target_severity
            grouped[finding_key]["severity"] = highest_severity

        # Convert to list and sort by severity
        result = list(grouped.values())
        result.sort(key=lambda x: severity_order.get(x.get("severity", "Low"), 0), reverse=True)
        return result

    def get_features(self) -> dict[str, bool]:
        features_list = self._request("GET", "/api/v2/features").json()["data"]
        return dict((v["key"], v["enabled"]) for v in features_list)

    def _get_tier_zero_group(self):
        try:
            response = self._request("GET", "/api/v2/asset-group-tags")
        except APIException as e:
            if e.http_code == 404:
                # PZ is off, use default
                return "admin_tier_0"
            raise
        # The tier zero tag is the one with type=1 and position=1
        for tag in response.json()["data"]["tags"]:
            if tag["type"] == 1 and tag["position"] == 1:
                return tag["name"]
        return None

    def get_data_quality(self, domain: Domain) -> dict:
        """
        Gets data quality stats for a domain from BHCE/EE.

        **Parameters:**

        ``domain: Domain``
            The domain to get data quality stats for from `/api/v2/available-domains`.
        """
        response = self._request("GET", "/api/v2/{idp_subdir}/{domain_id}/data-quality-stats?limit=1"
                                 .format(domain_id = domain["id"],
                                         idp_subdir = "ad-domains" if domain["type"] == "active-directory" else "azure-tenants"))
        payload = response.json()['data'][0]

        if domain["type"] == "active-directory":
            payload["session_completeness"] *= 100
            payload["local_group_completeness"] *= 100

        return payload

    def get_community_domains(self) -> list:
        """
        Gets domain info from BHCE/EE.
        """
        available_domains = self._request("GET", "/api/v2/available-domains").json()["data"]
        domains_out = []
        for domain in available_domains:
            domain_data = self._request("GET", f"/api/v2/domains/{domain['id']}").json()["data"]
            domain_out = {
                "name": domain_data["props"]["name"],
                "domain": domain_data["props"].get("domain"),
                "distinguished_name": domain_data["props"].get("distinguishedname"),
                "domain_sid": domain_data["props"].get("domainsid"),
                "functional_level": domain_data["props"].get("functionallevel"),
                "data_quality": self.get_data_quality(domain),
                "inbound_trusts": [],
                "outbound_trusts": [],
            }
            if domain_data.get("inboundTrusts", 0) > 0:
                domain_out["inbound_trusts"] = [{
                    "name": v["name"],
                } for v in self._request("GET", f"/api/v2/domains/{domain['id']}/inbound-trusts").json()["data"]]
            if domain_data.get("outboundTrusts", 0) > 0:
                domain_out["outbound_trusts"] = [{
                    "name": v["name"],
                } for v in self._request("GET", f"/api/v2/domains/{domain['id']}/outbound-trusts").json()["data"]]

            try:
                domain_computers = self._request("POST", "/api/v2/graphs/cypher", body=json.dumps({
                    "query": 'MATCH (n:Computer) WHERE n.domain = "{}" RETURN n'.format(domain['name']),
                    "include_properties": True,
                }).encode("utf-8")).json()["data"]
            except APIException as err:
                if isinstance(err.err_response, ErrorResponse) and err.http_code == 404:
                    # No results
                    domain_computers = {"nodes": {}}
                else:
                    raise
            domain_oses = Counter(
                value["properties"]["operatingsystem"]
                for value in domain_computers["nodes"].values()
                if "properties" in value and "operatingsystem" in value["properties"]
            )
            domain_out["computers"] = {
                "count": len(domain_computers),
                "operating_systems": domain_oses,
            }

            try:
                domain_users = self._request("POST", "/api/v2/graphs/cypher", body=json.dumps({
                    "query": 'MATCH (u:User) WHERE u.domain = "{}" RETURN u'.format(domain['name']),
                    "include_properties": True,
                }).encode("utf-8")).json()["data"]
            except APIException as err:
                if isinstance(err.err_response, ErrorResponse) and err.http_code == 404:
                    # No results
                    domain_users = {"nodes": {}}
                else:
                    raise

            pw_cutoff = datetime.now().timestamp() - 90*86400
            pw_old_count = 0
            for node in domain_users["nodes"].values():
                if "pwdlastset" not in node["properties"]:
                    continue
                last_set = node["properties"]["pwdlastset"]
                if last_set in (0, -1):
                    continue
                if last_set <= pw_cutoff:
                    pw_old_count += 1

            domain_out["users"] = {
                "count": len(domain_users["nodes"]),
                "with_old_pw": pw_old_count
            }

            domains_out.append(domain_out)

        return domains_out
