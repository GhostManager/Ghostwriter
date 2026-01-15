"""Tests for passive voice detector."""

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.modules.passive_voice.detector import PassiveVoiceDetector


class PassiveVoiceDetectorTests(TestCase):
    """Test suite for PassiveVoiceDetector."""

    def setUp(self):
        """Initialize detector for tests."""
        self.detector = PassiveVoiceDetector()

    def test_uses_configured_model(self):
        """Test that detector uses model from settings."""
        # pylint: disable=protected-access
        self.assertIsNotNone(self.detector._nlp)
        # Model name accessible via _nlp.meta
        self.assertIn("core_web_sm", self.detector._nlp.meta["name"])

    def test_detects_simple_passive_sentence(self):
        """Test detection of simple passive voice."""
        text = "The report was written by the team."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0], (0, len(text)))

    def test_ignores_active_voice(self):
        """Test that active voice is not flagged."""
        text = "The team wrote the report."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 0)

    def test_detects_multiple_passive_sentences(self):
        """Test detection of multiple passive sentences."""
        text = "The report was written. The findings were documented."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 2)

    def test_handles_empty_text(self):
        """Test handling of empty input."""
        ranges = self.detector.detect_passive_sentences("")
        self.assertEqual(len(ranges), 0)

    def test_handles_whitespace_only(self):
        """Test handling of whitespace-only input."""
        ranges = self.detector.detect_passive_sentences("   \n\t  ")
        self.assertEqual(len(ranges), 0)

    def test_handles_mixed_active_passive(self):
        """Test text with both active and passive voice."""
        text = "We tested the system. The vulnerabilities were exploited."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        self.assertIn("exploited", text[ranges[0][0] : ranges[0][1]])

    def test_singleton_pattern(self):
        """Test that detector uses singleton pattern."""
        detector1 = PassiveVoiceDetector()
        detector2 = PassiveVoiceDetector()

        self.assertIs(detector1, detector2)

    def test_passive_with_by_phrase(self):
        """Test passive voice with explicit by-phrase."""
        text = "The server was compromised by the attacker."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)

    def test_passive_without_by_phrase(self):
        """Test passive voice without by-phrase."""
        text = "The password was cracked."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)

    def test_complex_sentence_structure(self):
        """Test detection in complex sentences."""
        text = "After the system was analyzed, we found that credentials were stored in plaintext."
        ranges = self.detector.detect_passive_sentences(text)

        # Should detect 2 passive clauses
        self.assertGreaterEqual(len(ranges), 1)
