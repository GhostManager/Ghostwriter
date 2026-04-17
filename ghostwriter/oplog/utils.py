"""Utility functions for the Oplog application."""

# Standard Libraries
import gzip
import io
import json
import logging

# Django Imports
from django.conf import settings

logger = logging.getLogger(__name__)
CAST_PARSE_TOO_LARGE_WARNING = (
    "The recording file is too large to parse for search indexing. It was uploaded successfully, "
    "but it will not appear in search results."
)
CAST_DECOMPRESS_TOO_LARGE_WARNING = (
    "The recording file expands too large to parse safely. It was uploaded successfully, "
    "but it will not appear in search results."
)
CAST_INVALID_GZIP_UPLOAD_MESSAGE = "The gzip-compressed recording file is invalid."
CAST_GZIP_TOO_LARGE_UPLOAD_MESSAGE = (
    "The gzip-compressed recording expands too large for safe playback."
)


def get_cast_parse_input_bytes() -> int:
    """Return the raw-byte parsing cap based on the configured max upload size."""
    return getattr(settings, "GHOSTWRITER_MAX_FILE_SIZE", 10 * 1024 * 1024)


def get_cast_decompressed_bytes() -> int:
    """Allow a modest gzip expansion window while keeping parsing bounded."""
    return get_cast_parse_input_bytes() * 2


def _scan_gzip_size_limited(fileobj, max_output_bytes: int) -> tuple[int | None, str | None]:
    """Read a gzip stream safely, counting decompressed bytes without unbounded buffering."""
    total = 0
    try:
        with gzip.GzipFile(fileobj=fileobj) as gz_file:
            while True:
                chunk = gz_file.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_output_bytes:
                    logger.warning("Cast gzip payload exceeded safe decompression limit")
                    return None, CAST_GZIP_TOO_LARGE_UPLOAD_MESSAGE
    except (OSError, EOFError) as exc:
        logger.warning("Failed to decompress cast file: %s", exc)
        return None, CAST_INVALID_GZIP_UPLOAD_MESSAGE
    return total, None

def _strip_ansi_escapes(text: str) -> str:
    """
    Remove ANSI/VT100 escape sequences using a linear scan.

    This strips the same families covered previously by the regex:
    single-character Fe escapes, CSI sequences, and OSC sequences
    terminated by BEL or ST. Unterminated/unknown escape fragments are
    preserved as literal text.
    """
    cleaned = []
    index = 0
    length = len(text)

    while index < length:
        if text[index] != "\x1b":
            cleaned.append(text[index])
            index += 1
            continue

        if index + 1 >= length:
            cleaned.append(text[index])
            break

        next_char = text[index + 1]
        next_ord = ord(next_char)

        if next_char == "[":
            cursor = index + 2
            seen_intermediate = False
            while cursor < length:
                char_ord = ord(text[cursor])

                if 0x30 <= char_ord <= 0x3F and not seen_intermediate:
                    cursor += 1
                    continue

                if 0x20 <= char_ord <= 0x2F:
                    seen_intermediate = True
                    cursor += 1
                    continue

                if 0x40 <= char_ord <= 0x7E:
                    index = cursor + 1
                    break

                # Preserve malformed CSI text and continue from the invalid byte
                # so we do not rescan the tail and drift into quadratic behavior.
                cleaned.append(text[index:cursor])
                index = cursor
                break
            else:
                cleaned.append(text[index:])
                break
            continue

        if next_char == "]":
            cursor = index + 2
            while cursor < length:
                if text[cursor] == "\x07":
                    index = cursor + 1
                    break
                if text[cursor] == "\x1b" and cursor + 1 < length and text[cursor + 1] == "\\":
                    index = cursor + 2
                    break
                cursor += 1
            else:
                cleaned.append(text[index:])
                break
            continue

        # Fe escape sequences use a single final byte in the 0x40-0x5F range.
        if 0x40 <= next_ord <= 0x5F:
            index += 2
            continue

        cleaned.append(text[index])
        index += 1

    return "".join(cleaned)


def _decompress_gzip_limited(file_data: bytes, max_output_bytes: int) -> tuple[bytes | None, str | None]:
    """Decompress gzip data while enforcing a maximum output size."""
    out = bytearray()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(file_data)) as gz_file:
            while True:
                chunk = gz_file.read(min(64 * 1024, max_output_bytes - len(out) + 1))
                if not chunk:
                    break
                out.extend(chunk)
                if len(out) > max_output_bytes:
                    logger.warning("Cast gzip payload exceeded safe decompression limit")
                    return None, CAST_DECOMPRESS_TOO_LARGE_WARNING
    except (OSError, EOFError) as exc:
        logger.warning("Failed to decompress cast file: %s", exc)
        return None, "Could not decompress the recording file. It will not appear in search results."
    return bytes(out), None


def validate_cast_gzip_upload(fileobj) -> tuple[str | None, int | None]:
    """
    Validate that a .cast.gz file is well-formed and safe to hand to the browser.

    Returns ``(message, status_code)`` when the upload should be rejected, or
    ``(None, None)`` when the file is acceptable.
    """
    _, error = _scan_gzip_size_limited(fileobj, get_cast_decompressed_bytes())
    try:
        fileobj.seek(0)
    except (AttributeError, OSError):
        pass

    if error == CAST_GZIP_TOO_LARGE_UPLOAD_MESSAGE:
        return error, 413
    if error == CAST_INVALID_GZIP_UPLOAD_MESSAGE:
        return error, 400
    return None, None


def extract_cast_text(file_data: bytes) -> tuple[str, str | None]:
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
        if len(file_data) > get_cast_parse_input_bytes():
            logger.warning("Cast file exceeded safe parse input limit")
            return "", CAST_PARSE_TOO_LARGE_WARNING

        # Decompress if gzip-compressed (magic bytes 0x1f 0x8b)
        if file_data[:2] == b"\x1f\x8b":
            file_data, warning = _decompress_gzip_limited(file_data, get_cast_decompressed_bytes())
            if warning:
                return "", warning

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
                if version is None:
                    logger.warning("Missing version key in asciicast header")
                    return (
                        "",
                        "Missing version key in asciicast header. Only v2 and v3 are supported.",
                    )
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
                clean = _strip_ansi_escapes(str(event[2]))
                if clean:
                    parts.append(clean)

        return " ".join(parts), None

    except (UnicodeDecodeError, TypeError, AttributeError) as exc:
        logger.warning("Failed to extract text from cast file: %s", exc)
        return (
            "",
            "Could not parse the recording file. It will not appear in search results.",
        )
