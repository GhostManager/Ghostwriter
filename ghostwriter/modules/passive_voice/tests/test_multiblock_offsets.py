"""
Tests for passive voice detection with multi-block text.

These tests verify that character offsets are correctly calculated when
text contains multiple paragraphs/blocks separated by newlines (as returned
by TipTap's getText() method).

The server returns offsets relative to the plain text it receives. The frontend
must correctly map these offsets to ProseMirror document positions.

Issue: TipTap/ProseMirror uses document positions that account for node boundaries,
       not just text content. A paragraph like <p>Hello</p> has positions:
       - 0: before <p>
       - 1: before 'H'
       - 6: after 'o' (end of text)
       - 7: after </p>
"""

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.modules.passive_voice.detector import PassiveVoiceDetector


class MultiBlockOffsetTests(TestCase):
    """Test suite for multi-block text offset calculations."""

    def setUp(self):
        """Initialize detector for tests."""
        self.detector = PassiveVoiceDetector()

    def test_single_paragraph_offsets(self):
        """
        Test that offsets correctly point to the passive sentence text.

        Single paragraph: no node boundary complexity.
        """
        text = "The report was written by the team."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        start, end = ranges[0]

        # Verify the offset extracts the correct text
        extracted = text[start:end]
        self.assertEqual(extracted, text)
        self.assertIn("was written", extracted)

    def test_two_paragraph_offsets_passive_in_first(self):
        """
        Test offsets when passive voice is in the first paragraph.

        Text structure (as from getText()):
        "The report was written.\nThe team reviewed it."

        spaCy includes trailing whitespace/newline in sentence spans.
        """
        text = "The report was written.\nThe team reviewed it."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        start, end = ranges[0]

        extracted = text[start:end]
        # spaCy includes the newline in sentence boundaries
        self.assertIn("The report was written.", extracted)
        self.assertIn("was written", extracted)
        # Verify offset values
        self.assertEqual(start, 0)

    def test_two_paragraph_offsets_passive_in_second(self):
        """
        Test offsets when passive voice is in the second paragraph.

        Text structure:
        "The team wrote it.\nThe report was reviewed."

        Passive sentence starts at index 19 (after newline).
        """
        text = "The team wrote it.\nThe report was reviewed."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        start, end = ranges[0]

        extracted = text[start:end]
        self.assertEqual(extracted, "The report was reviewed.")
        # Verify offset values - second paragraph starts at index 19
        self.assertEqual(start, 19)
        self.assertEqual(end, 43)

    def test_multiple_paragraphs_mixed_voice(self):
        """
        Test offsets with multiple paragraphs containing mixed voice.

        Simulates realistic TipTap content with multiple blocks.
        spaCy includes trailing whitespace in sentence boundaries.
        """
        text = (
            "We tested the application.\n"
            "The vulnerability was exploited.\n"
            "Our team documented the findings."
        )
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        start, end = ranges[0]

        extracted = text[start:end]
        self.assertIn("The vulnerability was exploited.", extracted)
        # Second paragraph starts at index 27
        self.assertEqual(start, 27)

    def test_multiple_passive_across_paragraphs(self):
        """
        Test multiple passive sentences across different paragraphs.

        Ensures offsets are independent and correctly calculated for each.
        spaCy may include trailing whitespace in sentence boundaries.
        """
        text = (
            "The system was compromised.\n"
            "We investigated the incident.\n"
            "The credentials were stolen."
        )
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 2)

        # First passive sentence
        start1, end1 = ranges[0]
        self.assertIn("The system was compromised.", text[start1:end1])
        self.assertEqual(start1, 0)

        # Second passive sentence (third paragraph)
        start2, end2 = ranges[1]
        self.assertIn("The credentials were stolen.", text[start2:end2])
        # Third paragraph starts at 28 + 30 = 58
        self.assertEqual(start2, 58)

    def test_empty_paragraphs(self):
        """
        Test text with empty lines (double newlines).

        TipTap may produce consecutive newlines for empty paragraphs.
        """
        text = "Active sentence.\n\nThe report was written."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        start, end = ranges[0]

        extracted = text[start:end]
        self.assertEqual(extracted, "The report was written.")
        # After "Active sentence.\n\n" = 18 characters
        self.assertEqual(start, 18)

    def test_offset_extraction_matches_original_text(self):
        """
        Verify that using returned offsets to slice the original text
        always produces the detected passive sentence.

        This is the key contract: text[start:end] == detected sentence.
        """
        test_cases = [
            "The report was written.",
            "Active voice.\nThe report was written.",
            "First.\nSecond.\nThe report was written.",
            "The report was written.\nActive voice.",
        ]

        for text in test_cases:
            with self.subTest(text=text):
                ranges = self.detector.detect_passive_sentences(text)

                for start, end in ranges:
                    extracted = text[start:end]
                    # Extracted text should contain passive voice
                    self.assertIn("was written", extracted)
                    # Should be a complete sentence (ends with punctuation)
                    self.assertTrue(extracted.rstrip().endswith(('.', '!', '?')))

    def test_text_with_footnote_markers(self):
        """
        Test text containing footnote markers.

        In TipTap, footnotes are inline nodes that getText() renders as their
        text content. The frontend position mapper must account for these
        inline nodes when mapping offsets to document positions.

        Note: The server only sees plain text from getText(), so footnote
        content appears inline. The position mapping complexity is handled
        by the frontend's text_position_mapper.ts.

        TipTap's getText() renders footnote inline nodes with space separation,
        e.g., "written. 1" where "1" is the footnote content.
        """
        # Simulates getText() output when document contains a footnote
        # TipTap getText() adds space around inline node content
        text = "The report was written. 1\nSee the appendix for details."
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 1)
        start, end = ranges[0]

        extracted = text[start:end]
        self.assertIn("was written", extracted)
        self.assertEqual(start, 0)

    def test_text_with_multiple_inline_elements(self):
        """
        Test text with multiple inline elements (footnotes, evidence refs).

        TipTap's getText() flattens inline nodes to their text content.
        The server processes this as continuous text, unaware of node
        boundaries. Frontend must map positions correctly.

        Note: TipTap renders inline nodes with space separation in getText().
        """
        # Simulates complex document with inline elements (footnotes after sentences)
        # TipTap's getText() adds space around inline node content
        text = (
            "The system was compromised. 1\n"
            "We documented the findings. 2\n"
            "The credentials were stolen."
        )
        ranges = self.detector.detect_passive_sentences(text)

        self.assertEqual(len(ranges), 2)

        # First passive sentence (with footnote marker after period)
        start1, end1 = ranges[0]
        self.assertIn("was compromised", text[start1:end1])

        # Second passive sentence
        start2, end2 = ranges[1]
        self.assertIn("were stolen", text[start2:end2])
