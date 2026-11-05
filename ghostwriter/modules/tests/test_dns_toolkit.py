"""Compatibility tests for the asynchronous DNS collector."""

# Standard Libraries
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

# Django Imports
from django.test import SimpleTestCase

# 3rd Party Libraries
import dns.exception
import dns.message
import dns.rcode
import dns.rrset

# Ghostwriter Libraries
from ghostwriter.modules.dns_toolkit import DNSCollector


class DNSCollectorTests(SimpleTestCase):
    """Exercise the real resolver and answer parser without external DNS traffic."""

    records = {
        "A": "192.0.2.10",
        "NS": "ns.example.com.",
        "MX": "10 mail.example.com.",
        "TXT": '"v=spf1 -all"',
        "CNAME": "target.example.com.",
        "SOA": "ns.example.com. hostmaster.example.com. 1 3600 600 86400 60",
    }

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.addCleanup(self.close_loop)
        self.collector = DNSCollector()

    def close_loop(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    async def answer_query(self, query, *args, **kwargs):
        """Return a wire-round-tripped response through dnspython's UDP API."""
        response = dns.message.make_response(query)
        question = query.question[0]
        record_type = dns.rdatatype.to_text(question.rdtype)
        response.answer.append(
            dns.rrset.from_text(question.name, 60, "IN", record_type, self.records[record_type])
        )
        return dns.message.from_wire(response.to_wire())

    @patch("dns.asyncquery.udp")
    def test_batch_parses_supported_record_types(self, mock_udp):
        mock_udp.side_effect = self.answer_query
        domains = [SimpleNamespace(name="example.com"), SimpleNamespace(name="example.net")]

        results = self.collector.run_async_dns(domains, list(self.records))

        for domain in domains:
            expected = {"domain": domain.name}
            expected.update({f"{key.lower()}_record": [value] for key, value in self.records.items()})
            self.assertEqual(results[domain.name], expected)
        self.assertEqual(mock_udp.call_count, len(domains) * len(self.records))

    @patch("dns.asyncquery.udp")
    def test_dns_errors_are_returned_as_record_values(self, mock_udp):
        async def error_response(query, *args, **kwargs):
            response = dns.message.make_response(query)
            response.set_rcode(response_code)
            return response

        for response_code, expected in ((dns.rcode.NXDOMAIN, "NXDOMAIN"), (dns.rcode.NOERROR, "NoAnswer")):
            with self.subTest(expected=expected):
                mock_udp.side_effect = error_response
                results = self.collector.run_async_dns([SimpleNamespace(name="example.com")], ["A"])
                self.assertEqual(results["example.com"]["a_record"], expected)

    @patch("dns.asyncquery.udp")
    def test_timeout_is_returned_as_a_record_value(self, mock_udp):
        mock_udp.side_effect = dns.exception.Timeout
        # An immediate lifetime avoids waiting for the resolver's retry budget.
        with patch.object(self.collector.resolver, "lifetime", 0):
            results = self.collector.run_async_dns([SimpleNamespace(name="example.com")], ["A"])

        self.assertEqual(results["example.com"]["a_record"], "LifetimeTimeout")
