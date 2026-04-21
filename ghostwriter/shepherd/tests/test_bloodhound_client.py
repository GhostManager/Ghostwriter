import json
from unittest.mock import patch

from django.test import TestCase

from ghostwriter.shepherd.external.bloodhound.client import APIClient, Credentials, APIException, ErrorDetails, ErrorResponse


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

    def test_count_users_with_old_passwords_uses_numeric_query_first(self):
        captured_queries = []

        def fake_run(query):
            captured_queries.append(query)
            return 5

        with patch.object(self.client, "_run_cypher_count_query", side_effect=fake_run):
            result = self.client._count_users_with_old_passwords("EXAMPLE.LOCAL", 12345)

        self.assertEqual(result, 5)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn("u.pwdlastset <> 0", captured_queries[0])
        self.assertIn("u.pwdlastset <> -1", captured_queries[0])
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
