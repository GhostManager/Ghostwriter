"""Tests for YAML acronym upload feature."""

# Standard Libraries
import io

# Django Imports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.reporting.forms import AcronymYAMLUploadForm
from ghostwriter.reporting.models import Acronym


class AcronymYAMLUploadFormTests(TestCase):
    """Tests for the YAML upload form."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.user = UserFactory(password="testpassword", role="admin")

    def test_form_has_yaml_file_field(self):
        """Test form has yaml_file field."""
        form = AcronymYAMLUploadForm()
        self.assertIn("yaml_file", form.fields)

    def test_form_has_override_option(self):
        """Test form has override_existing field."""
        form = AcronymYAMLUploadForm()
        self.assertIn("override_existing", form.fields)

    def test_valid_yaml_file(self):
        """Test form accepts valid YAML file."""
        yaml_content = b"""CIA:
  - full: Central Intelligence Agency
NSA:
  - full: National Security Agency
"""
        yaml_file = SimpleUploadedFile("acronyms.yml", yaml_content, content_type="application/x-yaml")
        form = AcronymYAMLUploadForm(files={"yaml_file": yaml_file})
        self.assertTrue(form.is_valid())

    def test_missing_yaml_file(self):
        """Test form rejects missing file."""
        form = AcronymYAMLUploadForm(files={})
        self.assertFalse(form.is_valid())
        self.assertIn("yaml_file", form.errors)

    def test_invalid_yaml_syntax(self):
        """Test form rejects invalid YAML syntax."""
        yaml_content = b"""CIA:
  - full: Central Intelligence Agency
  invalid syntax here
"""
        yaml_file = SimpleUploadedFile("invalid.yml", yaml_content, content_type="application/x-yaml")
        form = AcronymYAMLUploadForm(files={"yaml_file": yaml_file})
        self.assertFalse(form.is_valid())
        self.assertIn("yaml_file", form.errors)

    def test_invalid_yaml_structure(self):
        """Test form rejects YAML with wrong structure."""
        yaml_content = b"""- Central Intelligence Agency
- National Security Agency
"""
        yaml_file = SimpleUploadedFile("wrong_structure.yml", yaml_content, content_type="application/x-yaml")
        form = AcronymYAMLUploadForm(files={"yaml_file": yaml_file})
        self.assertFalse(form.is_valid())
        self.assertIn("yaml_file", form.errors)

    def test_yaml_missing_required_fields(self):
        """Test form rejects YAML missing 'full' field."""
        yaml_content = b"""CIA:
"""
        yaml_file = SimpleUploadedFile("missing_fields.yml", yaml_content, content_type="application/x-yaml")
        form = AcronymYAMLUploadForm(files={"yaml_file": yaml_file})
        self.assertFalse(form.is_valid())
        self.assertIn("yaml_file", form.errors)

    def test_non_yaml_file_extension(self):
        """Test form rejects non-YAML file extensions."""
        content = b"some content"
        txt_file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        form = AcronymYAMLUploadForm(files={"yaml_file": txt_file})
        self.assertFalse(form.is_valid())
        self.assertIn("yaml_file", form.errors)


class AcronymYAMLImportTests(TestCase):
    """Tests for YAML import functionality."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.user = UserFactory(password="testpassword", role="admin")

    def test_import_creates_new_acronyms(self):
        """Test importing YAML creates new acronyms."""
        yaml_content = """CIA:
  - full: Central Intelligence Agency
NSA:
  - full: National Security Agency
"""
        from ghostwriter.reporting.utils import import_acronyms_from_yaml

        result = import_acronyms_from_yaml(yaml_content, override=False, user=self.user)

        self.assertEqual(Acronym.objects.count(), 2)
        self.assertEqual(result["created"], 2)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped"], 0)

    def test_import_skips_existing_acronyms(self):
        """Test importing existing acronyms without override skips them."""
        Acronym.objects.create(
            acronym="CIA",
            expansion="Central Intelligence Agency",
            created_by=self.user
        )

        yaml_content = """CIA:
  - full: Central Intelligence Agency
NSA:
  - full: National Security Agency
"""
        from ghostwriter.reporting.utils import import_acronyms_from_yaml

        result = import_acronyms_from_yaml(yaml_content, override=False, user=self.user)

        self.assertEqual(Acronym.objects.count(), 2)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 1)

    def test_import_updates_existing_with_override(self):
        """Test importing with override updates existing acronyms."""
        Acronym.objects.create(
            acronym="CIA",
            expansion="Old Expansion",
            created_by=self.user
        )

        yaml_content = """CIA:
  - full: Central Intelligence Agency
"""
        from ghostwriter.reporting.utils import import_acronyms_from_yaml

        result = import_acronyms_from_yaml(yaml_content, override=True, user=self.user)

        # Override creates new active entry and deactivates old ones
        self.assertEqual(Acronym.objects.filter(is_active=True).count(), 1)
        self.assertEqual(Acronym.objects.count(), 2)  # Old one still exists but inactive
        self.assertEqual(result["created"], 1)  # Created new one with override

        active_acronym = Acronym.objects.get(acronym="CIA", is_active=True)
        self.assertEqual(active_acronym.expansion, "Central Intelligence Agency")

    def test_import_handles_multiple_expansions(self):
        """Test importing acronym with multiple expansions."""
        yaml_content = """API:
  - full: Application Programming Interface
  - full: Advanced Persistent Infrastructure
"""
        from ghostwriter.reporting.utils import import_acronyms_from_yaml

        result = import_acronyms_from_yaml(yaml_content, override=False, user=self.user)

        self.assertEqual(Acronym.objects.filter(acronym="API").count(), 2)
        self.assertEqual(result["created"], 2)

    def test_import_sets_priority_by_order(self):
        """Test importing sets priority based on order in YAML."""
        yaml_content = """API:
  - full: Application Programming Interface
  - full: Advanced Persistent Infrastructure
"""
        from ghostwriter.reporting.utils import import_acronyms_from_yaml

        import_acronyms_from_yaml(yaml_content, override=False, user=self.user)

        first = Acronym.objects.filter(acronym="API", expansion__contains="Application").first()
        second = Acronym.objects.filter(acronym="API", expansion__contains="Advanced").first()

        self.assertGreater(first.priority, second.priority)

    def test_import_error_handling(self):
        """Test import handles errors gracefully."""
        yaml_content = "invalid: yaml: structure:"
        from ghostwriter.reporting.utils import import_acronyms_from_yaml

        with self.assertRaises(ValueError):
            import_acronyms_from_yaml(yaml_content, override=False, user=self.user)


class AcronymYAMLUploadViewTests(TestCase):
    """Tests for YAML upload view in admin interface."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.user = UserFactory(password="testpassword", role="admin")
        cls.user.is_staff = True
        cls.user.save()
        cls.uri = reverse("admin:reporting_acronym_upload_yaml")

    def setUp(self):
        """Log in the user before each test."""
        self.client.login(username=self.user.username, password="testpassword")

    def test_view_requires_login(self):
        """Test view requires authentication."""
        self.client.logout()
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/login/'))

    def test_view_requires_admin_user(self):
        """Test view requires staff user only."""
        regular_user = UserFactory(username="regular", password="testpass", role="user")
        regular_user.is_staff = False
        regular_user.save()
        self.client.logout()
        self.client.login(username=regular_user.username, password="testpass")
        response = self.client.get(self.uri)
        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/login/'))

    def test_view_get_uses_correct_template(self):
        """Test GET request uses correct template."""
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/reporting/acronym_upload_yaml.html")

    def test_view_post_valid_yaml(self):
        """Test POST with valid YAML creates acronyms."""
        yaml_content = b"""CIA:
  - full: Central Intelligence Agency
"""
        yaml_file = SimpleUploadedFile("acronyms.yml", yaml_content, content_type="application/x-yaml")

        response = self.client.post(self.uri, {"yaml_file": yaml_file, "override_existing": False})

        self.assertEqual(Acronym.objects.count(), 1)
        # Admin view redirects to ".." which resolves relative to current URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "..")

    def test_view_post_invalid_yaml_shows_errors(self):
        """Test POST with invalid YAML shows form errors."""
        yaml_content = b"invalid: yaml: syntax:"
        yaml_file = SimpleUploadedFile("invalid.yml", yaml_content, content_type="application/x-yaml")

        response = self.client.post(self.uri, {"yaml_file": yaml_file})

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("yaml_file", response.context["form"].errors)
        self.assertEqual(Acronym.objects.count(), 0)

    def test_view_displays_import_summary(self):
        """Test view displays import summary after successful upload."""
        yaml_content = b"""CIA:
  - full: Central Intelligence Agency
NSA:
  - full: National Security Agency
"""
        yaml_file = SimpleUploadedFile("acronyms.yml", yaml_content, content_type="application/x-yaml")

        response = self.client.post(self.uri, {"yaml_file": yaml_file, "override_existing": False}, follow=True)

        # Check we were redirected to admin changelist
        self.assertEqual(response.status_code, 200)
        # Check success message contains created count
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(len(messages_list) > 0)
        # The message should mention "2 acronym(s) created"
        message_text = str(messages_list[0])
        self.assertIn("2 acronym(s) created", message_text)
