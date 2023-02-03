# Standard Libraries
import logging

# Django Imports
from django.test import Client, TestCase, tag
from django.urls import reverse

logging.disable(logging.CRITICAL)


# Health checks for RAM and disk cannot be completed successfully in the GitHub CI/CD pipeline
@tag("GitHub")
class HealthCheckCustomViewTests(TestCase):
    """Collection of tests for :view:`status.HealthCheckCustomView`."""

    @classmethod
    def setUpTestData(cls):
        cls.uri = reverse("status:healthcheck")

    def setUp(self):
        self.client = Client()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "health_check.html")


class HealthCheckSimpleViewTests(TestCase):
    """Collection of tests for :view:`status.HealthCheckSimpleView`."""

    @classmethod
    def setUpTestData(cls):
        cls.uri = reverse("status:healthcheck_simple")

    def setUp(self):
        self.uri = reverse("status:healthcheck_simple")
        self.client = Client()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"OK", response.content)
