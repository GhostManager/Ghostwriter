"""Utility functions for the Oplog application."""

# Standard Libraries
import gzip
import json
import logging
import re

logger = logging.getLogger(__name__)

# Matches ANSI/VT100 escape sequences: CSI, SGR, OSC, cursor movement, etc.
_ANSI_ESCAPE_RE = re.compile(
    r"\x1b"
    r"(?:"
    r"[@-Z\\-_]"  # Fe escape sequences (e.g. \x1bO, \x1b7)
    r"|"
    r"\[[0-?]*[ -/]*[@-~]"  # CSI sequences (e.g. \x1b[0m, \x1b[32m, \x1b[2J)
    r"|"
    r"\][^\x07]*(?:\x07|\x1b\\)"  # OSC sequences terminated by BEL or ST
    r")"
)


def extract_cast_text(file_data: bytes) -> tuple:
    """
    Parse an asciicast v2 or v3 file and return ``(text, warning)``.

    Reads the format version from the header line. Extracts ``"i"`` (keyboard
    input) and ``"o"`` (terminal output) event data strings, strips ANSI escape
    sequences, and joins them into a single searchable text blob suitable for
    full-text indexing.

    Both v2 (absolute timestamps) and v3 (relative intervals) use the same
    ``[time, code, data]`` event array structure and identical ``"i"``/``"o"``
    event codes, so parsing is identical for both versions. v3 also permits
    comment lines prefixed with ``#``, which are skipped explicitly.

    Returns a 2-tuple:
        ``text``    -- the extracted, sanitized text (empty string on failure)
        ``warning`` -- a human-readable warning string, or ``None`` on success
    """
    try:
        # Decompress if gzip-compressed (magic bytes 0x1f 0x8b)
        if file_data[:2] == b"\x1f\x8b":
            try:
                file_data = gzip.decompress(file_data)
            except Exception as exc:
                logger.warning("Failed to decompress cast file: %s", exc)
                return (
                    "",
                    "Could not decompress the recording file. It will not appear in search results.",
                )

        text = file_data.decode("utf-8", errors="replace")
        lines = iter(text.splitlines())
        parts = []
        version = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # v3 supports comment lines; the first line must not be a comment
            if line.startswith("#"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(event, dict):
                # Header object — read version and move on to events
                version = event.get("version")
                if version not in (2, 3):
                    logger.warning("Unsupported asciicast version: %s", version)
                    return (
                        "",
                        f"Unsupported asciicast version ({version}). Only v2 and v3 are supported.",
                    )
                continue

            # Event line: [time, code, data]
            if not isinstance(event, list) or len(event) < 3:
                continue

            if event[1] in ("i", "o"):
                clean = _ANSI_ESCAPE_RE.sub("", str(event[2]))
                if clean:
                    parts.append(clean)

        return " ".join(parts), None

    except Exception as exc:
        logger.warning("Failed to extract text from cast file: %s", exc)
        return (
            "",
            "Could not parse the recording file. It will not appear in search results.",
        )
