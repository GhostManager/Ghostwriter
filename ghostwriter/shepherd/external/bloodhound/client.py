import base64
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class Credentials(object):
    def __init__(self, token_id: str, token_key: str) -> None:
        self.token_id = token_id
        self.token_key = token_key


class FindingsResponse(object):
    def __init__(self, findings, finding_assets) -> None:
        self.findings = findings
        self.finding_assets = finding_assets


class APIVersion(object):
    def __init__(self, current_api_version: str, deprecated_api_version: str, server_version: str) -> None:
        self.current_api_version = current_api_version
        self.deprecated_api_version = deprecated_api_version
        self.server_version = server_version


class Domain(object):
    def __init__(self, name: str, sid: str, collected: bool) -> None:
        self.name = name
        self.sid = sid
        self.collected = collected


class APIClient(object):
    def __init__(self, scheme: str, host: str, port: int, credentials: Credentials) -> None:
        self._scheme = scheme
        self._host = host
        self._port = port
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

        # If is no body content the HMAC digest is computed anyway, simply with no values written to the
        # digester.
        if body is not None:
            digester.update(body)

        # Perform the request with the signed and expected headers
        return requests.request(
            method=method,
            url=self._format_url(uri),
            headers={
                "User-Agent": "ghostwriter",
                "Authorization": f"bhesignature {self._credentials.token_id}",
                "RequestDate": datetime_formatted,
                "Signature": base64.b64encode(digester.digest()),
                "Content-Type": "application/json",
            },
            data=body,
        )

    def get_version(self) -> APIVersion:
        response = self._request("GET", "/api/version")
        payload = response.json()["data"]

        return APIVersion(current_api_version=payload["API"]["current_version"],
                          deprecated_api_version=payload["API"]["deprecated_version"],
                          server_version=payload["server_version"])

    def get_domains(self) -> list[Domain]:
        response = self._request("GET", "/api/v1/availabledomains")
        payload = response.json()

        domains = list()
        for domain in payload:
            domains.append(Domain(domain["name"], domain["id"], domain["collected"]))

        return domains

    def get_findings(self) -> FindingsResponse:
        response = self._request("GET", "/api/v2/attack-paths/details?accepted_until=lt:2025-06-03")
        payload = response.json()["data"]

        return FindingsResponse(findings=payload["findings"],
                                finding_assets=payload["finding_assets"])
