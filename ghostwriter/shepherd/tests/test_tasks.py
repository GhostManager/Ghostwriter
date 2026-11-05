"""Tests for Shepherd background tasks."""

# Standard Libraries
from unittest.mock import Mock, patch

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    DomainFactory,
    DomainStatusFactory,
    HealthStatusFactory,
    SlackConfigurationFactory,
    VirusTotalConfigurationFactory,
)
from ghostwriter.modules.review import DomainReview, VirusTotalRequestError
from ghostwriter.shepherd.tasks import check_domains


class DomainHealthTaskTests(TestCase):
    """Regression tests for VirusTotal-backed health updates."""

    def setUp(self):
        DomainStatusFactory(domain_status="Expired")
        healthy_status = HealthStatusFactory(health_status="Healthy")
        HealthStatusFactory(health_status="Burned")
        domain_status = DomainStatusFactory(domain_status="Available")
        self.domain = DomainFactory(
            domain_status=domain_status,
            health_status=healthy_status,
            categorization={"Existing source": "Existing category"},
        )
        VirusTotalConfigurationFactory(enable=True, sleep_time=0)
        SlackConfigurationFactory(enable=False)

    @patch("ghostwriter.modules.review.DomainReview.session.get")
    def test_rejected_virustotal_request_fails_without_updating_domain(self, mock_get):
        mock_get.return_value = Mock(ok=False, status_code=401)
        original_categories = self.domain.categorization.copy()
        original_health_check = self.domain.last_health_check

        with self.assertRaisesRegex(VirusTotalRequestError, r"HTTP 401"):
            check_domains()

        self.domain.refresh_from_db()
        self.assertEqual(self.domain.categorization, original_categories)
        self.assertEqual(self.domain.last_health_check, original_health_check)

    @patch("ghostwriter.modules.review.sleep")
    @patch("ghostwriter.modules.review.DomainReview.session.get")
    def test_missing_report_preserves_domain_and_continues_batch(self, mock_get, mock_sleep):
        other_domain = DomainFactory(
            domain_status=self.domain.domain_status,
            health_status=self.domain.health_status,
        )
        original_categories = self.domain.categorization.copy()
        original_health_check = self.domain.last_health_check
        original_health_status = self.domain.health_status_id
        original_explanation = self.domain.burned_explanation
        categories = {"Test vendor": "Business"}

        def domain_response(url, **kwargs):
            if url.endswith(f"/domains/{self.domain.name.lower()}"):
                return Mock(
                    ok=False,
                    status_code=404,
                    json=Mock(return_value={"error": {"code": "NotFoundError"}}),
                )
            return Mock(ok=True, json=Mock(return_value={"data": {"attributes": {"categories": categories}}}))

        mock_get.side_effect = domain_response

        results = check_domains()

        self.domain.refresh_from_db()
        other_domain.refresh_from_db()
        self.assertEqual(self.domain.categorization, original_categories)
        self.assertEqual(self.domain.last_health_check, original_health_check)
        self.assertEqual(self.domain.health_status_id, original_health_status)
        self.assertEqual(self.domain.burned_explanation, original_explanation)
        self.assertEqual(results[self.domain.pk]["change"], "error")
        self.assertIn("no report", results["errors"][self.domain.name])
        self.assertEqual(other_domain.categorization, categories)
        self.assertIsNotNone(other_domain.last_health_check)
        self.assertNotIn(other_domain.name, results["errors"])
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("ghostwriter.modules.review.DomainReview.session.get")
    def test_unrecognized_404_still_fails_without_updating_domain(self, mock_get):
        for response in (
            Mock(ok=False, status_code=404, json=Mock(side_effect=ValueError("Not JSON"))),
            Mock(ok=False, status_code=404, json=Mock(return_value={"error": {"code": "OtherError"}})),
        ):
            with self.subTest(response=response):
                mock_get.return_value = response
                with self.assertRaisesRegex(VirusTotalRequestError, r"HTTP 404") as raised:
                    check_domains(self.domain.pk)
                self.assertNotIn("API key", str(raised.exception))
                self.domain.refresh_from_db()
                self.assertIsNone(self.domain.last_health_check)

    @patch("ghostwriter.modules.review.DomainReview.session.get")
    def test_other_api_errors_remain_failures(self, mock_get):
        for status_code, guidance in ((403, "permissions"), (429, "quota"), (503, "HTTP 503")):
            with self.subTest(status_code=status_code):
                mock_get.return_value = Mock(ok=False, status_code=status_code)
                with self.assertRaisesRegex(VirusTotalRequestError, guidance):
                    check_domains(self.domain.pk)

    @patch("ghostwriter.modules.review.DomainReview.session.get")
    def test_subdomain_relationship_404_is_not_a_missing_domain_report(self, mock_get):
        mock_get.return_value = Mock(
            ok=False,
            status_code=404,
            json=Mock(return_value={"error": {"code": "NotFoundError"}}),
        )
        review = DomainReview([self.domain])

        with self.assertRaisesRegex(VirusTotalRequestError, r"HTTP 404"):
            review.get_domain_report(self.domain.name, subdomains=True)
