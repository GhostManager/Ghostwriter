"""Tests for the Acronym model."""

# Django Imports
from django.test import TestCase
from django.db import IntegrityError

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.reporting.models import Acronym


class AcronymModelTests(TestCase):
    """Collection of tests for the Acronym model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.user = UserFactory()

    def test_create_acronym(self):
        """Test creating a basic custom acronym."""
        acronym = Acronym.objects.create(
            acronym="TEST",
            expansion="Test Expansion String",
            created_by=self.user
        )
        self.assertEqual(acronym.acronym, "TEST")
        self.assertEqual(acronym.expansion, "Test Expansion String")
        self.assertTrue(acronym.is_active)
        self.assertFalse(acronym.override_builtin)
        self.assertEqual(acronym.priority, 0)
        self.assertEqual(acronym.created_by, self.user)

    def test_acronym_str_representation(self):
        """Test string representation of acronym."""
        acronym = Acronym.objects.create(
            acronym="API",
            expansion="Application Programming Interface",
            created_by=self.user
        )
        expected = "API → Application Programming Interface"
        self.assertEqual(str(acronym), expected)

    def test_acronym_str_truncation(self):
        """Test string representation truncates long expansions."""
        long_expansion = "A" * 100
        acronym = Acronym.objects.create(
            acronym="LONG",
            expansion=long_expansion,
            created_by=self.user
        )
        # Should truncate at 50 chars
        self.assertTrue(len(str(acronym)) < len(long_expansion) + 10)

    def test_acronym_ordering(self):
        """Test acronyms are ordered by acronym, then priority descending."""
        Acronym.objects.create(
            acronym="API",
            expansion="Version 1",
            priority=1,
            created_by=self.user
        )
        Acronym.objects.create(
            acronym="API",
            expansion="Version 2",
            priority=2,
            created_by=self.user
        )
        Acronym.objects.create(
            acronym="XSS",
            expansion="Cross-Site Scripting",
            priority=0,
            created_by=self.user
        )

        acronyms = list(Acronym.objects.all())
        # First two should be API (same acronym), ordered by priority desc
        self.assertEqual(acronyms[0].acronym, "API")
        self.assertEqual(acronyms[0].priority, 2)
        self.assertEqual(acronyms[1].acronym, "API")
        self.assertEqual(acronyms[1].priority, 1)
        # Last should be XSS
        self.assertEqual(acronyms[2].acronym, "XSS")

    def test_override_builtin_flag(self):
        """Test override_builtin flag can be set."""
        acronym = Acronym.objects.create(
            acronym="API",
            expansion="My Custom API Definition",
            override_builtin=True,
            created_by=self.user
        )
        self.assertTrue(acronym.override_builtin)

    def test_inactive_acronym(self):
        """Test acronym can be marked inactive."""
        acronym = Acronym.objects.create(
            acronym="OLD",
            expansion="Outdated Term",
            is_active=False,
            created_by=self.user
        )
        self.assertFalse(acronym.is_active)

    def test_filter_active_acronyms(self):
        """Test filtering for only active acronyms."""
        Acronym.objects.create(
            acronym="ACTIVE",
            expansion="Active Term",
            is_active=True,
            created_by=self.user
        )
        Acronym.objects.create(
            acronym="INACTIVE",
            expansion="Inactive Term",
            is_active=False,
            created_by=self.user
        )

        active_acronyms = Acronym.objects.filter(is_active=True)
        self.assertEqual(active_acronyms.count(), 1)
        self.assertEqual(active_acronyms.first().acronym, "ACTIVE")

    def test_acronym_without_created_by(self):
        """Test acronym can be created without user (system import)."""
        acronym = Acronym.objects.create(
            acronym="SYS",
            expansion="System Imported"
        )
        self.assertIsNone(acronym.created_by)

    def test_multiple_expansions_same_acronym(self):
        """Test same acronym can have multiple expansions."""
        Acronym.objects.create(
            acronym="CIA",
            expansion="Central Intelligence Agency",
            created_by=self.user
        )
        Acronym.objects.create(
            acronym="CIA",
            expansion="Confidentiality, Integrity, and Availability",
            created_by=self.user
        )

        cia_acronyms = Acronym.objects.filter(acronym="CIA")
        self.assertEqual(cia_acronyms.count(), 2)

    def test_timestamps_auto_populate(self):
        """Test created_at and updated_at timestamps."""
        acronym = Acronym.objects.create(
            acronym="TIME",
            expansion="Timestamp Test",
            created_by=self.user
        )
        self.assertIsNotNone(acronym.created_at)
        self.assertIsNotNone(acronym.updated_at)
        # Check timestamps are within 1 second of each other
        delta = acronym.updated_at - acronym.created_at
        self.assertLess(delta.total_seconds(), 1)

    def test_query_by_acronym_case_sensitive(self):
        """Test acronym queries are case-sensitive."""
        Acronym.objects.create(
            acronym="API",
            expansion="Application Programming Interface",
            created_by=self.user
        )

        # Exact match should work
        self.assertEqual(Acronym.objects.filter(acronym="API").count(), 1)
        # Different case should not match
        self.assertEqual(Acronym.objects.filter(acronym="api").count(), 0)
