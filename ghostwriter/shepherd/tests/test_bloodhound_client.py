import json
import logging
from unittest.mock import patch

from django.test import TestCase

from ghostwriter.reporting.models import Severity
from ghostwriter.shepherd.external.bloodhound.client import (
    APIClient,
    Credentials,
    APIException,
    ErrorDetails,
    ErrorResponse
)

logging.disable(logging.CRITICAL)


class MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class BloodHoundClientTests(TestCase):
    def setUp(self):
        self.client = APIClient(
            scheme="https",
            host="bloodhound.example",
            port=443,
            credentials=Credentials(token_id="id", token_key="key"),
        )
        Severity.objects.bulk_create(
            [
                Severity(severity="Critical", weight=1, color="966FD6"),
                Severity(severity="High", weight=2, color="FF7E79"),
                Severity(severity="Moderate", weight=3, color="F4B083"),
                Severity(severity="Low", weight=4, color="A8D08D"),
            ]
        )

    def test_get_community_domains_uses_aggregate_cypher_queries(self):
        queries = []

        def fake_request(method, uri, body=None):
            if method == "GET" and uri == "/api/v2/available-domains":
                return MockResponse(
                    {
                        "data": [
                            {
                                "id": "domain-id",
                                "name": "EXAMPLE.LOCAL",
                                "type": "active-directory",
                            }
                        ]
                    }
                )

            if method == "GET" and uri == "/api/v2/domains/domain-id?counts=false":
                return MockResponse(
                    {
                        "data": {
                            "props": {
                                "name": "EXAMPLE.LOCAL",
                                "domain": "EXAMPLE.LOCAL",
                                "distinguishedname": "DC=EXAMPLE,DC=LOCAL",
                                "domainsid": "S-1-5-21-123",
                                "functionallevel": "2016",
                            }
                        }
                    }
                )

            if method == "GET" and uri == "/api/v2/ad-domains/domain-id/data-quality-stats?limit=1":
                return MockResponse(
                    {
                        "data": [
                            {
                                "groups": 7,
                                "sessions": 3,
                                "gpos": 2,
                                "acls": 11,
                                "relationships": 13,
                                "session_completeness": 0.5,
                                "local_group_completeness": 0.75,
                            }
                        ]
                    }
                )

            if method == "GET" and uri == "/api/v2/domains/domain-id/inbound-trusts?skip=0&limit=128":
                return MockResponse({"data": [{"name": "TRUSTED.LOCAL"}]})

            if method == "GET" and uri == "/api/v2/domains/domain-id/outbound-trusts?skip=0&limit=128":
                return MockResponse({"data": [{"name": "LEGACY.LOCAL"}]})

            if method == "POST" and uri == "/api/v2/graphs/cypher":
                query = json.loads(body.decode("utf-8"))["query"]
                queries.append(query)

                if "RETURN n.operatingsystem AS operating_system, count(n) AS count" in query:
                    return MockResponse(
                        {
                            "data": {
                                "literals": [
                                    {"key": "operating_system", "value": "Windows 11"},
                                    {"key": "count", "value": 10},
                                    {"key": "operating_system", "value": "Windows Server 2022"},
                                    {"key": "count", "value": 32},
                                ]
                            }
                        }
                    )

                if "RETURN count(n) AS count" in query and "Computer" in query:
                    return MockResponse({"data": {"literals": [{"key": "count", "value": 42}]}})

                if "RETURN count(u) AS count" in query and "pwdlastset" not in query:
                    return MockResponse({"data": {"literals": [{"key": "count", "value": 100}]}})

                if "u.pwdlastset <= " in query:
                    return MockResponse({"data": {"literals": [{"key": "count", "value": 2}]}})

            raise AssertionError(f"Unexpected request: {method} {uri} {body!r}")

        with patch.object(self.client, "_request", side_effect=fake_request):
            result = self.client.get_community_domains()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["computers"]["count"], 42)
        self.assertEqual(result[0]["computers"]["operating_systems"]["Windows 11"], 10)
        self.assertEqual(
            result[0]["computers"]["operating_systems"]["Windows Server 2022"], 32
        )
        self.assertEqual(result[0]["users"]["count"], 100)
        self.assertEqual(result[0]["users"]["with_old_pw"], 2)
        self.assertTrue(all("RETURN n" != query[-8:] for query in queries))
        self.assertTrue(all("RETURN u" != query[-8:] for query in queries))
        self.assertTrue(all("RETURN n " not in query for query in queries))
        self.assertTrue(all("RETURN u " not in query for query in queries))
        self.assertEqual(
            sum("RETURN n.operatingsystem AS operating_system, count(n) AS count" in query for query in queries),
            1,
        )

    def test_get_all_marks_empty_instances(self):
        with patch.object(self.client, "get_enterprise_findings", return_value=[]), patch.object(
            self.client, "get_community_domains", return_value=[]
        ):
            result = self.client.get_all()

        self.assertTrue(result["empty"])
        self.assertIn("no domains or findings yet", result["status_message"])

    def test_escape_cypher_string_escapes_quotes_and_backslashes(self):
        escaped = self.client._escape_cypher_string('EXAMPLE\\"LOCAL')
        self.assertEqual(escaped, 'EXAMPLE\\\\\\"LOCAL')

    def test_run_cypher_literal_query_filters_for_requested_alias(self):
        def fake_request(method, uri, body=None):
            self.assertEqual(method, "POST")
            self.assertEqual(uri, "/api/v2/graphs/cypher")
            payload = json.loads(body.decode("utf-8"))
            self.assertEqual(payload["query"], "MATCH (n) RETURN count(n) AS count")
            self.assertFalse(payload["include_properties"])
            return MockResponse(
                {
                    "data": {
                        "literals": [
                            {"key": "unexpected", "value": 99},
                            {"key": "count", "value": 3},
                            {"key": "count", "value": 4},
                        ]
                    }
                }
            )

        with patch.object(self.client, "_request", side_effect=fake_request):
            result = self.client._run_cypher_literal_query(
                "MATCH (n) RETURN count(n) AS count",
                "count",
            )

        self.assertEqual(result, [3, 4])

    def test_run_cypher_count_query_returns_zero_for_missing_or_invalid_counts(self):
        cases = [
            [],
            ["not-an-int"],
        ]

        for values in cases:
            with self.subTest(values=values):
                with patch.object(self.client, "_run_cypher_literal_query", return_value=values):
                    result = self.client._run_cypher_count_query(
                        "MATCH (n) RETURN count(n) AS count"
                    )
                self.assertEqual(result, 0)

    def test_get_data_quality_returns_defaults_when_api_has_no_stats_yet(self):
        def fake_request(method, uri, body=None):
            self.assertEqual(method, "GET")
            self.assertEqual(uri, "/api/v2/ad-domains/domain-id/data-quality-stats?limit=1")
            return MockResponse({"data": []})

        with patch.object(self.client, "_request", side_effect=fake_request):
            result = self.client.get_data_quality(
                {"id": "domain-id", "name": "EXAMPLE.LOCAL", "type": "active-directory"}
            )

        self.assertEqual(
            result,
            {
                "groups": 0,
                "sessions": 0,
                "gpos": 0,
                "acls": 0,
                "relationships": 0,
                "session_completeness": 0,
                "local_group_completeness": 0,
            },
        )

    def test_count_users_with_old_passwords_uses_numeric_query_first(self):
        captured_queries = []

        def fake_run(query):
            captured_queries.append(query)
            return 5

        with patch.object(self.client, "_run_cypher_count_query", side_effect=fake_run):
            result = self.client._count_users_with_old_passwords("EXAMPLE.LOCAL", 12345)

        self.assertEqual(result, 5)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn("u.enabled = true", captured_queries[0])
        self.assertIn("NOT u.pwdlastset IN [-1, 0]", captured_queries[0])
        self.assertIn("u.pwdlastset <= 12345", captured_queries[0])
        self.assertNotIn('"12345"', captured_queries[0])

    def test_count_users_with_old_passwords_falls_back_to_string_query_for_text_schema(self):
        captured_queries = []
        type_error = APIException(
            "API request failed with status code 500",
            err_response=ErrorResponse(
                status=None,
                timestamp="2026-04-20T20:31:08.815875974Z",
                request_id="req-id",
                errors=[ErrorDetails(context="", message="ERROR: operator does not exist: text <> integer (SQLSTATE 42883)")],
            ),
            http_code=500,
        )

        def fake_run(query):
            captured_queries.append(query)
            if len(captured_queries) == 1:
                raise type_error
            return 2

        with patch.object(self.client, "_run_cypher_count_query", side_effect=fake_run):
            result = self.client._count_users_with_old_passwords("EXAMPLE.LOCAL", 12345)

        self.assertEqual(result, 2)
        self.assertEqual(len(captured_queries), 2)
        self.assertIn("u.pwdlastset <= 12345", captured_queries[0])
        self.assertIn('u.pwdlastset <= "12345"', captured_queries[1])

    def test_get_enterprise_findings_uses_exposure_for_relationship_findings_with_source_id_key(self):
        finding_name = "TierZeroGenericWrite"
        payload = {
            "data": {
                "findings": [
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "source_id": "SRC-1",
                        "source_kind": "User",
                        "target_id": "TGT-1",
                        "target_kind": "Group",
                        "impact_percentage": 0.99,
                        "exposure_percentage": 0.01,
                        "asset_group": "tier-zero",
                    }
                ],
                "finding_assets": {
                    finding_name: {
                        "title.md": "VGl0bGU=",
                        "type.md": "VHlwZQ==",
                        "references.md": "",
                        "short_description.md": "",
                        "long_description.md": "",
                        "short_remediation.md": "",
                        "long_remediation.md": "",
                    }
                },
            }
        }

        with patch.object(self.client, "_request", return_value=MockResponse(payload)), patch.object(
            self.client, "get_features", return_value={}
        ):
            result = self.client.get_enterprise_findings()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["severity"], "Low")
        self.assertEqual(result[0]["principals"][0]["severity"], "Low")

    def test_get_enterprise_findings_keeps_large_default_groups_on_impact_path(self):
        finding_name = "LargeDefaultGroupsGenericAll"
        payload = {
            "data": {
                "findings": [
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "sourceid": "EXAMPLE-S-1-1-0",
                        "source_kind": "Group",
                        "target_id": "TGT-1",
                        "target_kind": "Container",
                        "impact_percentage": 0,
                        "exposure_percentage": 0.9801,
                        "asset_group": "tier-zero",
                    }
                ],
                "finding_assets": {
                    finding_name: {
                        "title.md": "VGl0bGU=",
                        "type.md": "VHlwZQ==",
                        "references.md": "",
                        "short_description.md": "",
                        "long_description.md": "",
                        "short_remediation.md": "",
                        "long_remediation.md": "",
                    }
                },
            }
        }

        with patch.object(self.client, "_request", return_value=MockResponse(payload)), patch.object(
            self.client, "get_features", return_value={}
        ):
            result = self.client.get_enterprise_findings()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["severity"], "Low")
        self.assertEqual(result[0]["principals"][0]["severity"], "Low")

    def test_get_enterprise_findings_keeps_distinct_source_target_pairs(self):
        finding_name = "TierZeroGenericWrite"
        payload = {
            "data": {
                "findings": [
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "sourceid": "SRC-1",
                        "source_kind": "User",
                        "target_id": "TGT-1",
                        "target_kind": "Group",
                        "impact_percentage": 0.2,
                        "exposure_percentage": 0.2,
                        "asset_group": "tier-zero",
                    },
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "sourceid": "SRC-2",
                        "source_kind": "User",
                        "target_id": "TGT-1",
                        "target_kind": "Group",
                        "impact_percentage": 0.2,
                        "exposure_percentage": 0.2,
                        "asset_group": "tier-zero",
                    },
                ],
                "finding_assets": {
                    finding_name: {
                        "title.md": "VGl0bGU=",
                        "type.md": "VHlwZQ==",
                        "references.md": "",
                        "short_description.md": "",
                        "long_description.md": "",
                        "short_remediation.md": "",
                        "long_remediation.md": "",
                    }
                },
            }
        }

        with patch.object(self.client, "_request", return_value=MockResponse(payload)), patch.object(
            self.client, "get_features", return_value={}
        ):
            result = self.client.get_enterprise_findings()

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["principals"]), 2)
        self.assertEqual(
            {(principal["source_id"], principal["target_id"]) for principal in result[0]["principals"]},
            {("SRC-1", "TGT-1"), ("SRC-2", "TGT-1")},
        )

    def test_get_enterprise_findings_uses_asset_group_tag_id_for_tier_zero_assets(self):
        finding_name = "TierZeroGenericWrite"
        payload = {
            "data": {
                "findings": [
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "target_id": "TGT-1",
                        "target_kind": "Group",
                        "impact_percentage": 0.2,
                        "asset_group_tag_id": 42,
                    }
                ],
                "finding_assets": {
                    finding_name: {
                        "title.md": "VGllciBaZXJvIFRpdGxl",
                        "tx-title.md": "Tm9uLVRpZXIgWmVybyBUaXRsZQ==",
                        "type.md": "VHlwZQ==",
                        "references.md": "",
                        "short_description.md": "",
                        "long_description.md": "",
                        "short_remediation.md": "",
                        "long_remediation.md": "",
                    }
                },
            }
        }

        with patch.object(self.client, "_request", return_value=MockResponse(payload)), patch.object(
            self.client, "get_features", return_value={"tier_management_engine": True}
        ), patch.object(self.client, "_get_tier_zero_group", return_value={"id": 42, "name": "custom-tier-zero"}):
            result = self.client.get_enterprise_findings()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["assets"]["title"], "Non-Tier Zero Title")
        self.assertTrue(result[0]["is_tier_zero"])

    def test_get_enterprise_findings_ignores_malformed_tier_zero_tag_without_id(self):
        finding_name = "TierZeroGenericWrite"
        payload = {
            "data": {
                "findings": [
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "target_id": "TGT-1",
                        "target_kind": "Group",
                        "impact_percentage": 0.2,
                    }
                ],
                "finding_assets": {
                    finding_name: {
                        "title.md": "VGllciBaZXJvIFRpdGxl",
                        "tx-title.md": "Tm9uLVRpZXIgWmVybyBUaXRsZQ==",
                        "type.md": "VHlwZQ==",
                        "references.md": "",
                        "short_description.md": "",
                        "long_description.md": "",
                        "short_remediation.md": "",
                        "long_remediation.md": "",
                    }
                },
            }
        }

        with patch.object(self.client, "_request", return_value=MockResponse(payload)), patch.object(
            self.client, "get_features", return_value={"tier_management_engine": True}
        ), patch.object(self.client, "_get_tier_zero_group", return_value={"name": "custom-tier-zero"}):
            result = self.client.get_enterprise_findings()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["assets"]["title"], "Tier Zero Title")
        self.assertFalse(result[0]["is_tier_zero"])

    def test_get_enterprise_findings_treats_invalid_percentages_as_zero(self):
        finding_name = "TierZeroGenericWrite"
        payload = {
            "data": {
                "findings": [
                    {
                        "finding_name": finding_name,
                        "environment_id": "S-1-5-21-1",
                        "sourceid": "SRC-1",
                        "source_kind": "User",
                        "target_id": "TGT-1",
                        "target_kind": "Group",
                        "impact_percentage": 0.99,
                        "exposure_percentage": None,
                        "asset_group_tag_id": 1,
                    }
                ],
                "finding_assets": {
                    finding_name: {
                        "title.md": "VGl0bGU=",
                        "type.md": "VHlwZQ==",
                        "references.md": "",
                        "short_description.md": "",
                        "long_description.md": "",
                        "short_remediation.md": "",
                        "long_remediation.md": "",
                    }
                },
            }
        }

        with patch.object(self.client, "_request", return_value=MockResponse(payload)), patch.object(
            self.client, "get_features", return_value={}
        ):
            result = self.client.get_enterprise_findings()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["severity"], "Low")
        self.assertEqual(result[0]["principals"][0]["severity"], "Low")
