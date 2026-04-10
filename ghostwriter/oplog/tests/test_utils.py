# Standard Libraries
import gzip
import unittest

# Ghostwriter Libraries
from ghostwriter.oplog.utils import extract_cast_text


class ExtractCastTextTests(unittest.TestCase):
    """Unit tests for :func:`ghostwriter.oplog.utils.extract_cast_text`."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _v2(self, events=""):
        header = b'{"version": 2, "width": 80, "height": 24}\n'
        return header + events.encode()

    def _v3(self, events=""):
        header = b'{"version": 3, "term": {"cols": 80, "rows": 24}}\n'
        return header + events.encode()

    # ------------------------------------------------------------------
    # Version detection
    # ------------------------------------------------------------------

    def test_v2_output_events_extracted(self):
        """v2 files are parsed correctly: 'o' event data is returned."""
        text, warning = extract_cast_text(self._v2('[0.5, "o", "hello world"]\n'))
        self.assertIsNone(warning)
        self.assertIn("hello world", text)

    def test_v3_output_events_extracted(self):
        """v3 files are parsed correctly: 'o' event data is returned."""
        text, warning = extract_cast_text(self._v3('[0.5, "o", "v3 output"]\n'))
        self.assertIsNone(warning)
        self.assertIn("v3 output", text)

    def test_v2_input_events_extracted(self):
        """'i' (keyboard input) events are included in v2 files."""
        text, warning = extract_cast_text(self._v2('[0.5, "i", "ls\\r"]\n'))
        self.assertIsNone(warning)
        self.assertIn("ls", text)

    def test_v3_input_and_output_events_extracted(self):
        """Both 'i' and 'o' event data are included in v3 files."""
        events = '[0.5, "o", "prompt>"]\n[1.0, "i", "whoami"]\n'
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertIn("prompt>", text)
        self.assertIn("whoami", text)

    def test_unsupported_version_1_returns_warning(self):
        """asciicast v1 is a different format and not supported."""
        data = b'{"version": 1, "width": 80, "height": 24}\n[0.5, "o", "never"]\n'
        text, warning = extract_cast_text(data)
        self.assertEqual(text, "")
        self.assertIsNotNone(warning)
        self.assertIn("1", warning)

    def test_unknown_version_returns_warning(self):
        """An unrecognised version number returns an empty string and a warning."""
        data = b'{"version": 99, "width": 80, "height": 24}\n[0.5, "o", "never"]\n'
        text, warning = extract_cast_text(data)
        self.assertEqual(text, "")
        self.assertIsNotNone(warning)

    def test_missing_version_key_returns_warning(self):
        """A header object with no 'version' key is treated as unsupported."""
        data = b'{"width": 80, "height": 24}\n[0.5, "o", "never"]\n'
        text, warning = extract_cast_text(data)
        self.assertEqual(text, "")
        self.assertIsNotNone(warning)

    # ------------------------------------------------------------------
    # v3-specific: comment lines
    # ------------------------------------------------------------------

    def test_v3_comment_lines_skipped(self):
        """Lines starting with '#' (v3 comments) are silently skipped."""
        raw = (
            b'{"version": 3, "term": {"cols": 80, "rows": 24}}\n'
            b"# this is a comment\n"
            b'[0.5, "o", "after comment"]\n'
            b"# another comment\n"
            b'[1.0, "o", "also included"]\n'
        )
        text, warning = extract_cast_text(raw)
        self.assertIsNone(warning)
        self.assertIn("after comment", text)
        self.assertIn("also included", text)

    # ------------------------------------------------------------------
    # Event type filtering
    # ------------------------------------------------------------------

    def test_non_io_events_excluded(self):
        """'r' (resize), 'm' (marker), and 'x' (exit) events do not appear in output."""
        events = '[0.5, "r", "100x40"]\n[1.0, "m", "checkpoint"]\n[1.5, "x", "0"]\n'
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertEqual(text, "")

    def test_mixed_event_types_only_io_captured(self):
        """Only 'i' and 'o' payloads appear; resize, marker, and exit payloads are excluded."""
        events = (
            '[0.1, "o", "output text"]\n'
            '[0.2, "r", "120x40"]\n'
            '[0.3, "i", "input text"]\n'
            '[0.4, "m", ""]\n'
            '[0.5, "x", "0"]\n'
        )
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertIn("output text", text)
        self.assertIn("input text", text)
        self.assertNotIn("120x40", text)

    # ------------------------------------------------------------------
    # ANSI stripping
    # ------------------------------------------------------------------

    def test_ansi_color_sequences_stripped(self):
        r"""SGR colour codes (\x1b[32m, \x1b[0m) are removed from extracted text."""
        # In JSON '\u001b' is the ESC character (0x1b)
        events = '[0.5, "o", "\\u001b[32mgreen\\u001b[0m"]\n'
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertNotIn("\x1b", text)
        self.assertIn("green", text)

    def test_ansi_cursor_movement_stripped(self):
        r"""CSI cursor/erase sequences (\x1b[2J, \x1b[H) are removed."""
        events = '[0.5, "o", "\\u001b[2J\\u001b[Htext"]\n'
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertNotIn("\x1b", text)
        self.assertIn("text", text)

    # ------------------------------------------------------------------
    # Gzip support
    # ------------------------------------------------------------------

    def test_gzip_file_decompressed_and_parsed(self):
        """Gzip-compressed files are transparently decompressed before parsing."""
        inner = self._v3('[0.5, "o", "compressed output"]\n')
        text, warning = extract_cast_text(gzip.compress(inner))
        self.assertIsNone(warning)
        self.assertIn("compressed output", text)

    def test_invalid_gzip_returns_warning(self):
        """Bytes beginning with the gzip magic number but not valid gzip return a warning."""
        text, warning = extract_cast_text(b"\x1f\x8b\x00\x00this is not gzip")
        self.assertEqual(text, "")
        self.assertIsNotNone(warning)

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_bytes_returns_empty_string_no_warning(self):
        """An empty input produces ('', None) without error."""
        text, warning = extract_cast_text(b"")
        self.assertEqual(text, "")
        self.assertIsNone(warning)

    def test_file_with_no_io_events_returns_empty_string(self):
        """A valid file containing only non-io events returns an empty text blob."""
        text, warning = extract_cast_text(self._v3('[0.5, "r", "80x24"]\n[1.0, "m", ""]\n'))
        self.assertEqual(text, "")
        self.assertIsNone(warning)

    def test_malformed_json_lines_skipped_gracefully(self):
        """JSON parse errors on individual event lines do not abort processing."""
        raw = (
            b'{"version": 3, "term": {"cols": 80, "rows": 24}}\n'
            b"not json at all\n"
            b'[0.5, "o", "valid"]\n'
            b"{broken\n"
        )
        text, warning = extract_cast_text(raw)
        self.assertIsNone(warning)
        self.assertIn("valid", text)

    def test_short_event_array_skipped(self):
        """Arrays with fewer than 3 elements are silently skipped."""
        raw = (
            b'{"version": 3, "term": {"cols": 80, "rows": 24}}\n'
            b'[0.5, "o"]\n'
            b'[1.0, "o", "ok"]\n'
        )
        text, warning = extract_cast_text(raw)
        self.assertIsNone(warning)
        self.assertEqual(text, "ok")

    def test_multiple_events_joined_with_space(self):
        """Text from multiple events is joined into a single space-delimited blob."""
        events = '[0.1, "o", "first"]\n[0.2, "o", "second"]\n[0.3, "o", "third"]\n'
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertEqual(text, "first second third")

    def test_empty_event_data_after_ansi_strip_excluded(self):
        """An event whose data reduces to empty after ANSI stripping is not added to output."""
        # '\u001b[0m' stripped to '' — must not add an empty token before 'real'
        events = '[0.5, "o", "\\u001b[0m"]\n[0.6, "o", "real"]\n'
        text, warning = extract_cast_text(self._v3(events))
        self.assertIsNone(warning)
        self.assertEqual(text, "real")
