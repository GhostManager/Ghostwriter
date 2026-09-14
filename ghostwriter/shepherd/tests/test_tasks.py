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
from ghostwriter.modules.review import VirusTotalRequestError
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
