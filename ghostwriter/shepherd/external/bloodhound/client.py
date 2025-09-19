# Standard Libraries
import base64
import hashlib
import hmac
import logging

from datetime import datetime
from typing import Literal, Optional, NamedTuple, Dict, Any, List

# Django Imports
from django.conf import settings

# 3rd Party Libraries
import requests

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
    status: int
    timestamp: str
    request_id: str
    errors: List[ErrorDetails]

    @classmethod
    def from_json_dict(cls, json_dict: Dict[str, Any]) -> "ErrorResponse":
        errors: List[ErrorDetails] = []

        for error_details_json in json_dict["errors"]:
            errors.append(ErrorDetails.from_json_dict(error_details_json))

        return ErrorResponse(
            status=json_dict["status"],
            timestamp=json_dict["timestamp"],
            request_id=json_dict["request_id"],
            errors=errors,
        )

class APIException(Exception):
    def __init__(self, msg: str, err_response: ErrorResponse = None) -> None:
        self.msg = msg
        self.err_response = err_response


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
        )

        if response.status_code < 200:
            raise APIException(msg=f"API response received with unexpected status code {response.status_code}")

        if response.status_code >= 400:
            # Attempt to read an error response object from the API response
            err_response = ErrorResponse.from_json_dict(response.json())
            raise APIException(msg=f"API request failed with status code {response.status_code}",
                               err_response=err_response)

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

    def get_enterprise_findings(self) -> dict:
        response = self._request("GET", "/api/v2/attack-paths/details")
        payload = response.json()["data"]
        return payload
