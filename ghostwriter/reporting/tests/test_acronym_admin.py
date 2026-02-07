"""Tests for the Acronym admin interface."""

# Django Imports
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.reporting.admin import AcronymAdmin
from ghostwriter.reporting.models import Acronym


class AcronymAdminTests(TestCase):
    """Tests for the Acronym admin interface."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.user = UserFactory(password="testpassword", role="admin")
        cls.site = AdminSite()
        cls.factory = RequestFactory()

    def test_acronym_admin_is_registered(self):
        """Test that Acronym model is registered in admin."""
        from django.contrib import admin
        self.assertIn(Acronym, admin.site._registry)

    def test_acronym_admin_list_display(self):
        """Test admin list_display shows correct fields."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        expected = ("acronym", "expansion", "priority", "override_builtin", "is_active", "created_by")
        self.assertEqual(admin_instance.list_display, expected)

    def test_acronym_admin_list_filter(self):
        """Test admin list_filter includes correct fields."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        expected = ("is_active", "override_builtin", "created_by")
        self.assertEqual(admin_instance.list_filter, expected)

    def test_acronym_admin_search_fields(self):
        """Test admin search_fields includes acronym and expansion."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        expected = ("acronym", "expansion")
        self.assertEqual(admin_instance.search_fields, expected)

    def test_acronym_admin_list_editable(self):
        """Test admin allows inline editing of is_active and priority."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        expected = ("is_active", "priority")
        self.assertEqual(admin_instance.list_editable, expected)

    def test_acronym_admin_ordering(self):
        """Test admin orders by acronym then priority descending."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        expected = ("acronym", "-priority")
        self.assertEqual(admin_instance.ordering, expected)

    def test_acronym_admin_fieldsets(self):
        """Test admin fieldsets are properly organized."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        self.assertIsNotNone(admin_instance.fieldsets)
        # Should have 2 sections: General Information and Metadata
        self.assertEqual(len(admin_instance.fieldsets), 2)

        # Check General Information section
        general_section = admin_instance.fieldsets[0]
        self.assertEqual(general_section[0], "General Information")
        self.assertIn("acronym", general_section[1]["fields"])
        self.assertIn("expansion", general_section[1]["fields"])

        # Check Metadata section
        metadata_section = admin_instance.fieldsets[1]
        self.assertEqual(metadata_section[0], "Metadata")
        self.assertIn("priority", metadata_section[1]["fields"])
        self.assertIn("override_builtin", metadata_section[1]["fields"])
        self.assertIn("is_active", metadata_section[1]["fields"])

    def test_acronym_admin_readonly_fields(self):
        """Test created_by, created_at, updated_at are read-only."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        expected = ("created_by", "created_at", "updated_at")
        self.assertEqual(admin_instance.readonly_fields, expected)

    def test_acronym_admin_actions(self):
        """Test custom admin actions are available."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        # Actions can be strings (method names) or tuples, extract names
        action_names = []
        for action in admin_instance.actions:
            if isinstance(action, str):
                action_names.append(action)
            elif callable(action):
                action_names.append(action.__name__)
        self.assertIn("activate_acronyms", action_names)
        self.assertIn("deactivate_acronyms", action_names)

    def test_activate_acronyms_action(self):
        """Test activate_acronyms action marks acronyms as active."""
        from unittest.mock import Mock

        # Create inactive acronyms
        acronym1 = Acronym.objects.create(
            acronym="TEST1", expansion="Test 1", is_active=False, created_by=self.user
        )
        acronym2 = Acronym.objects.create(
            acronym="TEST2", expansion="Test 2", is_active=False, created_by=self.user
        )

        admin_instance = AcronymAdmin(Acronym, self.site)
        request = Mock()

        queryset = Acronym.objects.filter(pk__in=[acronym1.pk, acronym2.pk])
        admin_instance.activate_acronyms(request, queryset)

        acronym1.refresh_from_db()
        acronym2.refresh_from_db()
        self.assertTrue(acronym1.is_active)
        self.assertTrue(acronym2.is_active)

    def test_deactivate_acronyms_action(self):
        """Test deactivate_acronyms action marks acronyms as inactive."""
        from unittest.mock import Mock

        # Create active acronyms
        acronym1 = Acronym.objects.create(
            acronym="TEST3", expansion="Test 3", is_active=True, created_by=self.user
        )
        acronym2 = Acronym.objects.create(
            acronym="TEST4", expansion="Test 4", is_active=True, created_by=self.user
        )

        admin_instance = AcronymAdmin(Acronym, self.site)
        request = Mock()

        queryset = Acronym.objects.filter(pk__in=[acronym1.pk, acronym2.pk])
        admin_instance.deactivate_acronyms(request, queryset)

        acronym1.refresh_from_db()
        acronym2.refresh_from_db()
        self.assertFalse(acronym1.is_active)
        self.assertFalse(acronym2.is_active)

    def test_acronym_admin_save_model_sets_created_by(self):
        """Test save_model auto-sets created_by on new objects."""
        admin_instance = AcronymAdmin(Acronym, self.site)
        request = self.factory.get("/admin/reporting/acronym/add/")
        request.user = self.user

        acronym = Acronym(acronym="NEW", expansion="New Acronym")
        admin_instance.save_model(request, acronym, None, False)  # False = new object

        self.assertEqual(acronym.created_by, self.user)

    def test_acronym_admin_does_not_overwrite_created_by(self):
        """Test save_model doesn't overwrite existing created_by."""
        other_user = UserFactory(username="otheruser", role="user")
        acronym = Acronym.objects.create(
            acronym="EXIST", expansion="Existing", created_by=other_user
        )

        admin_instance = AcronymAdmin(Acronym, self.site)
        request = self.factory.get(f"/admin/reporting/acronym/{acronym.pk}/change/")
        request.user = self.user

        acronym.expansion = "Updated Expansion"
        admin_instance.save_model(request, acronym, None, False)

        acronym.refresh_from_db()
        self.assertEqual(acronym.created_by, other_user)
