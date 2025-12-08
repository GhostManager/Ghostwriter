"""Extended DocxTemplate with support for additional templated parts."""

from __future__ import annotations

import fnmatch
import html
import io
import logging
import re
import zipfile
import posixpath
from collections import defaultdict, deque
from copy import deepcopy
import operator
from typing import Iterator

from docx.oxml import parse_xml
from docxtpl.template import DocxTemplate
from jinja2 import Environment, meta, Undefined, TemplateSyntaxError
from docx.opc.packuri import PackURI
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
try:
    from jinja2.debug import Traceback as JinjaTraceback
except Exception:  # pragma: no cover - depends on optional Jinja debug support
    JinjaTraceback = None  # type: ignore[assignment]
from lxml import etree


_JINJA_STATEMENT_RE = re.compile(r"({[{%#].*?[}%]})", re.DOTALL)
_INLINE_STRING_TYPES = {"inlineStr"}
_XML_TAG_GAP = r"(?:\s|</?(?:[A-Za-z_][\w.-]*:)?[A-Za-z_][\w.-]*[^>]*>)*"
_RELATIONSHIP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_RELATIONSHIP_PREFIX = f"{{{_RELATIONSHIP_NS}}}"
_WORDPROCESSING_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_WORD2010_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
_HYPERLINK_RELTYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
)
_COMMENTS_EXTENDED_PART = "word/commentsExtended.xml"
_COMMENTS_EXTENDED_RELTYPE_2011 = (
    "http://schemas.microsoft.com/office/2011/relationships/commentsExtended"
)
_COMMENTS_EXTENDED_RELTYPE_2017 = (
    "http://schemas.microsoft.com/office/2017/06/relationships/commentsExtended"
)
_MS_COMMENTS_EXTENDED_CONTENT_TYPE = "application/vnd.ms-word.commentsExtended+xml"
_SETTINGS_PARTNAME = "word/settings.xml"
_APP_PROPERTIES_PART = "docProps/app.xml"
_APP_PROPERTIES_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
)
_VTYPES_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
)
_DOCUMENT_PARTNAME = "word/document.xml"

_INDEXED_PART_RE = re.compile(
    r"^(?P<folder>word/(?:charts|embeddings))/(?P<prefix>[^/]+?)(?P<index>\d+)(?P<suffix>\.[A-Za-z0-9_.-]+)$"
)
_BOOKMARK_FIELD_RE = re.compile(
    r"""\b(?:REF|PAGEREF|NOTEREF)\b[^\w"']*(?:"([A-Za-z0-9_:.\-]+)"|([A-Za-z0-9_:.\-]+))""",
    re.IGNORECASE,
)
_BOOKMARK_HYPERLINK_FIELD_RE = re.compile(
    r"""\\l\s+"?([A-Za-z0-9_:.\-]+)"?""",
    re.IGNORECASE,
)


logger = logging.getLogger(__name__)


class GhostwriterDocxTemplate(DocxTemplate):
    """Docx template that also renders SmartArt diagram parts.

    Microsoft Word stores SmartArt data in the ``word/diagrams`` folder of the
    DOCX package. The python-docx-template library does not process those XML
    parts when rendering a document or when collecting undeclared variables for
    linting.  This subclass extends the renderer so those parts participate in
    templating just like the document body.
    """

    _EXTRA_TEMPLATED_PATTERNS: tuple[str, ...] = (
        "word/diagrams/data*.xml",
        "word/diagrams/drawing*.xml",
        "word/embeddings/Microsoft_Excel_Worksheet*.xlsx",
        "word/charts/chart*.xml",
    )

    _DOCUMENT_REQUIRED_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
        {
            f"{_RELATIONSHIP_NS}/styles",
            f"{_RELATIONSHIP_NS}/stylesWithEffects",
            f"{_RELATIONSHIP_NS}/numbering",
            f"{_RELATIONSHIP_NS}/fontTable",
            f"{_RELATIONSHIP_NS}/settings",
            f"{_RELATIONSHIP_NS}/theme",
            f"{_RELATIONSHIP_NS}/webSettings",
            f"{_RELATIONSHIP_NS}/glossaryDocument",
            f"{_RELATIONSHIP_NS}/comments",
            f"{_RELATIONSHIP_NS}/commentAuthors",
            f"{_RELATIONSHIP_NS}/footnotes",
            f"{_RELATIONSHIP_NS}/endnotes",
            f"{_RELATIONSHIP_NS}/people",
            _COMMENTS_EXTENDED_RELTYPE_2011,
            _COMMENTS_EXTENDED_RELTYPE_2017,
            "http://schemas.microsoft.com/office/2011/relationships/comments",
        }
    )

    def render(self, context, jinja_env=None, autoescape: bool = False) -> None:  # type: ignore[override]
        """Render the template, including SmartArt diagram XML parts."""

        # Initialisation mirrors :meth:`docxtpl.template.DocxTemplate.render` so we
        # can hook additional parts into the rendering pipeline while reusing the
        # base implementation for the main document.
        self.render_init()

        if autoescape:
            if not jinja_env:
                jinja_env = Environment(autoescape=autoescape)
            else:
                jinja_env.autoescape = autoescape

        active_env = jinja_env or getattr(self, "jinja_env", None)
        if active_env is None:
            active_env = Environment(autoescape=autoescape) if autoescape else Environment()
        jinja_env = active_env
        self._install_numeric_tests(active_env)
        self.jinja_env = active_env
        self._referenced_comment_ids: set[str] = set()

        xml_src = self.build_xml(context, jinja_env)
        tree = self.fix_tables(xml_src)
        self.fix_docpr_ids(tree)
        tree = self._cleanup_word_markup(self.docx._part, tree)
        self.map_tree(tree)
        self._cleanup_part_relationships(self.docx._part, tree)

        headers = self.build_headers_footers_xml(context, self.HEADER_URI, jinja_env)
        for rel_key, xml in headers:
            rel = self.docx._part.rels.get(rel_key) if self.docx and self.docx._part else None
            header_part = rel.target_part if rel else None
            cleaned_xml = self._cleanup_word_markup(header_part, xml)
            self.map_headers_footers_xml(rel_key, cleaned_xml)
            if header_part:
                self._cleanup_part_relationships(header_part, cleaned_xml)

        footers = self.build_headers_footers_xml(context, self.FOOTER_URI, jinja_env)
        for rel_key, xml in footers:
            rel = self.docx._part.rels.get(rel_key) if self.docx and self.docx._part else None
            footer_part = rel.target_part if rel else None
            cleaned_xml = self._cleanup_word_markup(footer_part, xml)
            self.map_headers_footers_xml(rel_key, cleaned_xml)
            if footer_part:
                self._cleanup_part_relationships(footer_part, cleaned_xml)

        self._cleanup_settings_part()
        self._render_additional_parts(context, jinja_env)
        self._cleanup_comments_part()

        self._renumber_media_parts()

        self._normalise_package_content_types()

        self.render_properties(context, jinja_env)

        self._repair_app_properties()

        self.is_rendered = True

    def get_undeclared_template_variables(self, jinja_env=None):  # type: ignore[override]
        """Return undeclared variables, including those in SmartArt parts."""

        self.init_docx(reload=False)

        xml_sources: list[tuple[str, str]] = [
            (self._describe_part(getattr(self.docx, "_part", None)), self.patch_xml(self.get_xml()))
        ]
        for uri in (self.HEADER_URI, self.FOOTER_URI):
            for _rel_key, part in self.get_headers_footers(uri):
                xml_sources.append((self._describe_part(part), self.patch_xml(self.get_part_xml(part))))

        for part in self._iter_additional_parts():
            partname = self._normalise_partname(part)
            if self._is_excel_part(partname):
                infos_files = self._read_excel_part(part)
                if infos_files is None:
                    continue
                _infos, files = infos_files
                files = self._inline_templated_shared_strings(files)
                for name, data in files.items():
                    if not name.endswith(".xml"):
                        continue
                    label = f"{partname}:{name}"
                    xml_sources.append((label, self.patch_xml(data.decode("utf-8"))))
            else:
                xml_sources.append((self._describe_part(part), self.patch_xml(self.get_part_xml(part))))

        env = jinja_env or getattr(self, "jinja_env", None) or Environment()

        undeclared: set[str] = set()
        for label, xml in xml_sources:
            try:
                parse_content = env.parse(xml)
            except Exception as exc:
                self._log_template_parse_error(exc, [(label, xml)])
                if isinstance(exc, TemplateSyntaxError):
                    location, context_line = self._extract_template_part_context(
                        exc, [(label, xml)]
                    )
                    raise ReportExportTemplateError(
                        f"Template syntax error: {exc}", location, context_line
                    ) from exc
                raise
            undeclared.update(meta.find_undeclared_variables(parse_content))

        return undeclared

    def _extract_template_part_context(
        self, exc: BaseException, xml_sources: list[tuple[str, str]]
    ) -> tuple[str | None, str | None]:
        """Return the part label and context line for a template syntax error."""

        error_line = getattr(exc, "lineno", None) or self._extract_template_error_line(exc)
        current_line = 1
        for label, xml in xml_sources:
            line_count = xml.count("\n") + 1
            if error_line is None:
                return label, None
            start_line = current_line
            end_line = current_line + line_count - 1
            if start_line <= error_line <= end_line:
                relative_line = error_line - start_line
                lines = xml.splitlines()
                if 0 <= relative_line < len(lines):
                    return label, self._trim_template_text(lines[relative_line])
                return label, None
            current_line = end_line + 1

        return None, None

    def _log_template_parse_error(
        self, exc: BaseException, xml_sources: list[tuple[str, str]]
    ) -> None:
        """Log contextual information when parsing template parts fails."""

        error_line = getattr(exc, "lineno", None) or self._extract_template_error_line(exc)
        part_label: str | None = None
        part_line: int | None = None
        part_xml: str | None = None
        current_line = 1

        for label, xml in xml_sources:
            line_count = xml.count("\n") + 1
            if error_line is None:
                part_label = label
                part_xml = xml
                break

            start_line = current_line
            end_line = current_line + line_count - 1
            if start_line <= error_line <= end_line:
                part_label = label
                part_xml = xml
                part_line = error_line - start_line + 1
                break
            current_line = end_line + 1

        error_context: list[tuple[int, str]] = []
        if part_xml and part_line is not None:
            lines = part_xml.splitlines()
            start = max(part_line - 3, 0)
            end = min(part_line + 2, len(lines))
            for index in range(start, end):
                error_context.append((index + 1, self._trim_template_text(lines[index])))

        statements: list[dict[str, str | int]] = []
        total_statements = 0
        if part_xml:
            statements, total_statements = self._collect_template_statements(
                part_xml, focus_line=part_line
            )

        message_parts: list[str] = []
        if part_line is not None and part_label:
            message_parts.append(
                f"error near template line {part_line} in {part_label}"
            )
        elif error_line is not None:
            message_parts.append(f"error near template line {error_line}")
        if error_context:
            message_parts.append(self._format_template_context(error_context, part_line))
        if statements:
            message_parts.append(self._format_statement_preview(statements, total_statements))

        logger.exception(
            "Failed to parse DOCX template while collecting undeclared variables%s",
            f" in {part_label}" if part_label else "",
            extra={
                "docx_template_part": part_label,
                "docx_template_error_line": part_line or error_line,
                "docx_template_statements_preview": statements,
                "docx_template_statement_count": total_statements,
                **(
                    {
                        "docx_template_error_context": [
                            {"line": line, "text": text}
                            for line, text in error_context
                        ]
                    }
                    if error_context
                    else {}
                ),
            },
        )
        if message_parts:
            logger.error("; ".join(message_parts))

    def patch_xml(self, src_xml):  # type: ignore[override]
        """Normalize XML for templating across Word body and SmartArt parts."""

        patched = super().patch_xml(src_xml)
        patched = self._strip_excel_table_tags(patched)

        def strip_namespaced_tags(match: re.Match[str]) -> str:
            statement = match.group(0)
            cleaned: list[str] = []
            in_single = False
            in_double = False
            idx = 0

            while idx < len(statement):
                char = statement[idx]
                if char == "'" and not in_double:
                    in_single = not in_single
                    cleaned.append(char)
                    idx += 1
                    continue
                if char == '"' and not in_single:
                    in_double = not in_double
                    cleaned.append(char)
                    idx += 1
                    continue
                if char == "<" and not in_single and not in_double:
                    end = statement.find(">", idx)
                    if end == -1:
                        cleaned.append(char)
                        idx += 1
                        continue
                    idx = end + 1
                    continue

                cleaned.append(char)
                idx += 1

            return "".join(cleaned)

        return _JINJA_STATEMENT_RE.sub(strip_namespaced_tags, patched)

    def _strip_excel_table_tags(self, xml: str) -> str:
        """Remove Excel row/cell wrappers around Ghostwriter ``tr``/``tc`` tags."""

        has_spreadsheet_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main" in xml

        if has_spreadsheet_ns:

            def _strip_container(value: str, container: str, tag: str) -> str:
                open_regex = "<(?:[A-Za-z_][\\w.-]*:)?%s[^>]*>\\s*%s\\s*%s"
                close_regex = "%s.*?%s\\s*</(?:[A-Za-z_][\\w.-]*:)?%s>"
                for start, end, start_regex in (
                    ("{{", "}}", "\\{\\{"),
                    ("{%", "%}", "\\{%"),
                    ("{#", "#}", "\\{#"),
                ):
                    open_pattern = re.compile(
                        open_regex % (container, start_regex, tag),
                        re.DOTALL,
                    )
                    value = open_pattern.sub(start, value)
                    close_pattern = re.compile(
                        close_regex % (start_regex, end, container),
                        re.DOTALL,
                    )

                    def close_replacement(match: re.Match[str]) -> str:
                        matched = match.group(0)
                        end_index = matched.rfind(end)
                        return matched[: end_index + len(end)] if end_index != -1 else matched

                    value = close_pattern.sub(close_replacement, value)

                return re.sub(r"(\{\{|\{%|\{#)\s+", lambda m: m.group(1) + " ", value)

            xml = _strip_container(xml, "row", "tr")
            xml = _strip_container(xml, "c", "tc")

        def _replace_open_tr(match: re.Match[str]) -> str:
            trim = match.group("trim") or ""
            return "{%" + trim + " for"

        def _replace_close_tr(match: re.Match[str]) -> str:
            trim = match.group("trim") or ""
            return "{%" + trim + " endfor"

        open_tr_pattern = re.compile(
            r"\{%(?P<trim>-?)" + _XML_TAG_GAP + r"tr" + _XML_TAG_GAP + r"for\b",
        )
        close_tr_pattern = re.compile(
            r"\{%(?P<trim>-?)"
            + _XML_TAG_GAP
            + r"(?:endtr|tr"
            + _XML_TAG_GAP
            + r"endfor)\b",
        )
        xml = open_tr_pattern.sub(_replace_open_tr, xml)
        xml = close_tr_pattern.sub(_replace_close_tr, xml)

        if has_spreadsheet_ns:
            row_wrapper_pattern = re.compile(
                r"<row[^>]*>"
                r"(?:\s|<[^>]+>)*"
                r"(?P<stmt>\{%-?\s*(?:for\b[^%]*|endfor)\s*-?%})"
                r"(?:\s|</[^>]+>)*"
                r"</row>",
                re.DOTALL,
            )

            def _unwrap_row(match: re.Match[str]) -> str:
                return match.group("stmt")

            xml = row_wrapper_pattern.sub(_unwrap_row, xml)

        tc_pattern = re.compile(
            r"(\{[\{%#]-?)(" + _XML_TAG_GAP + r")tc\b",
        )

        def _strip_tc(match: re.Match[str]) -> str:
            gap = match.group(2)
            next_char = match.string[match.end() : match.end() + 1]
            if gap and gap[-1].isspace() and next_char and next_char.isspace():
                gap = gap[:-1]
            return match.group(1) + gap

        xml = tc_pattern.sub(_strip_tc, xml)
        return xml

    # ------------------------------------------------------------------
    # Helpers

    def _iter_additional_parts(self) -> Iterator:
        """Yield DOCX parts that should be templated in addition to the body."""

        if not self.docx:
            return

        seen: set[str] = set()
        for part in self._iter_reachable_parts():
            if part is self.docx._part:
                continue

            partname = self._normalise_partname(part)
            if partname in seen:
                continue
            if self._matches_extra_template(partname):
                seen.add(partname)
                yield part

    def _iter_reachable_parts(self) -> Iterator:
        """Yield parts reachable from the main document via relationships."""

        if not self.docx or not self.docx._part:
            return

        queue: deque = deque([self.docx._part])
        seen = {self.docx._part}

        while queue:
            part = queue.popleft()
            yield part

            rels = getattr(part, "rels", None)
            if not rels:
                continue

            for rel in rels.values():
                if getattr(rel, "is_external", False):
                    continue

                try:
                    target = getattr(rel, "target_part", None)
                except ValueError:
                    continue
                if target is None or target in seen:
                    continue
                seen.add(target)
                queue.append(target)

    def _normalise_package_content_types(self) -> None:
        parts = self._iter_package_parts()
        if not parts:
            return

        for part in parts:
            if self._normalise_partname(part) != _COMMENTS_EXTENDED_PART:
                continue
            current = getattr(part, "content_type", None)
            if current == _MS_COMMENTS_EXTENDED_CONTENT_TYPE:
                return
            setattr(part, "_content_type", _MS_COMMENTS_EXTENDED_CONTENT_TYPE)
            return

    def _repair_app_properties(self) -> None:
        parts = self._iter_package_parts()
        if not parts:
            return

        app_part = None
        for part in parts:
            try:
                partname = self._normalise_partname(part)
            except Exception:
                continue
            if partname == _APP_PROPERTIES_PART:
                app_part = part
                break

        if app_part is None:
            return

        raw_xml = self.get_part_xml(app_part)
        if isinstance(raw_xml, bytes):
            xml_text = raw_xml.decode("utf-8", errors="ignore")
        else:
            xml_text = raw_xml

        try:
            root = etree.fromstring(xml_text.encode("utf-8"))
        except (etree.XMLSyntaxError, AttributeError):
            return

        namespaces = {k or "ep": v for k, v in root.nsmap.items() if v}
        namespaces.setdefault("ep", _APP_PROPERTIES_NS)
        namespaces.setdefault("vt", _VTYPES_NS)

        titles_vector = root.find(".//ep:TitlesOfParts/vt:vector", namespaces)
        if titles_vector is None:
            return

        heading_vector = root.find(".//ep:HeadingPairs/vt:vector", namespaces)
        vt_ns = namespaces.get("vt")
        vt_prefix = f"{{{vt_ns}}}" if vt_ns else ""

        lpstr_nodes: list = []
        for child in list(titles_vector):
            qname = etree.QName(child)
            if qname.namespace == vt_ns and qname.localname == "lpstr":
                lpstr_nodes.append(child)
                continue
            if qname.namespace == vt_ns and qname.localname == "variant":
                inner = child.find(f".//{vt_prefix}lpstr")
                if inner is not None:
                    lpstr_nodes.append(inner)

        expected_count = 0
        if heading_vector is not None:
            for variant in heading_vector.findall(f"{vt_prefix}variant"):
                count_node = variant.find(f".//{vt_prefix}i4")
                if count_node is None or count_node.text is None:
                    continue
                try:
                    expected_count += int(count_node.text)
                except ValueError:
                    continue

        fallback_total = max(len(lpstr_nodes), expected_count)
        fallback_label = "Document {}" if fallback_total > 1 else "Document"

        if not lpstr_nodes:
            new_node = etree.SubElement(titles_vector, f"{vt_prefix}lpstr")
            new_node.text = (
                fallback_label.format(1)
                if "{}" in fallback_label
                else fallback_label
            )
            lpstr_nodes.append(new_node)

        for index, node in enumerate(lpstr_nodes):
            text = (node.text or "").strip()
            if text:
                continue
            node.text = (
                fallback_label.format(index + 1)
                if "{}" in fallback_label
                else fallback_label
            )

        while expected_count and len(lpstr_nodes) < expected_count:
            new_node = etree.SubElement(titles_vector, f"{vt_prefix}lpstr")
            new_node.text = (
                fallback_label.format(len(lpstr_nodes) + 1)
                if "{}" in fallback_label
                else fallback_label
            )
            lpstr_nodes.append(new_node)

        titles_vector.set("size", str(len(lpstr_nodes)))

        if (
            heading_vector is not None
            and expected_count
            and lpstr_nodes
        ):
            i4_nodes = [
                variant.find(f".//{vt_prefix}i4")
                for variant in heading_vector.findall(f"{vt_prefix}variant")
            ]
            i4_nodes = [node for node in i4_nodes if node is not None]
            if len(i4_nodes) == 1:
                i4_nodes[0].text = str(len(lpstr_nodes))

        output_bytes = etree.tostring(root, encoding="utf-8")
        output_xml = output_bytes.decode("utf-8")

        if hasattr(app_part, "_element"):
            try:
                app_part._element = parse_xml(output_xml)
            except Exception:
                app_part._element = etree.fromstring(output_bytes)

        if hasattr(app_part, "_blob"):
            app_part._blob = output_bytes

    def _iter_package_parts(self) -> list:
        doc = getattr(self, "docx", None)
        main_part = getattr(doc, "_part", None) if doc is not None else None
        package = getattr(main_part, "package", None)
        if package is None:
            return []

        iter_parts = getattr(package, "iter_parts", None)
        parts: list = []

        if callable(iter_parts):
            try:
                parts = list(iter_parts())
            except Exception:
                parts = []

        if not parts:
            parts_source = getattr(package, "parts", None)
            if isinstance(parts_source, dict):
                parts = list(parts_source.values())
            elif parts_source is not None:
                try:
                    parts = list(parts_source)
                except TypeError:
                    try:
                        parts = list(parts_source())  # type: ignore[operator]
                    except Exception:
                        parts = []

        return [part for part in parts if not isinstance(part, PackURI)]

    def _is_document_part(self, part) -> bool:
        partname = getattr(part, "partname", None)
        if not partname:
            return False
        try:
            normalised = str(partname).lstrip("/")
        except Exception:
            return False
        return normalised == _DOCUMENT_PARTNAME

    def _ensure_modern_comments_relationship(self, rels) -> None:
        if not rels:
            return

        for rel in rels.values():
            reltype = getattr(rel, "reltype", "")
            if reltype != _COMMENTS_EXTENDED_RELTYPE_2011:
                continue
            self._set_relationship_type(rel, _COMMENTS_EXTENDED_RELTYPE_2017)

    @staticmethod
    def _set_relationship_type(rel, reltype: str) -> None:
        if hasattr(rel, "_reltype"):
            try:
                setattr(rel, "_reltype", reltype)
            except Exception:
                pass
        try:
            setattr(rel, "reltype", reltype)
        except Exception:
            pass

    @staticmethod
    def _install_numeric_tests(env: Environment) -> None:
        """Install numeric comparison tests that tolerate ``None`` and undefined values."""

        comparators = {
            "gt": operator.gt,
            "ge": operator.ge,
            "lt": operator.lt,
            "le": operator.le,
        }

        for name, comparator in comparators.items():
            env.tests[name] = GhostwriterDocxTemplate._make_numeric_test(comparator)

    @staticmethod
    def _make_numeric_test(comparator):
        def _test(value, other):
            coerced_value = GhostwriterDocxTemplate._coerce_numeric(value)
            coerced_other = GhostwriterDocxTemplate._coerce_numeric(other)
            try:
                return comparator(coerced_value, coerced_other)
            except TypeError:
                return False

        return _test

    @staticmethod
    def _coerce_numeric(value):
        if isinstance(value, Undefined) or value is None:
            return 0
        return value

    def _matches_extra_template(self, partname: str) -> bool:
        return any(fnmatch.fnmatch(partname, pattern) for pattern in self._EXTRA_TEMPLATED_PATTERNS)

    def _normalise_partname(self, part) -> str:
        return str(part.partname).lstrip("/")

    def _describe_indexed_part(self, part) -> tuple[str | None, str | None, str | None]:
        try:
            partname = self._normalise_partname(part)
        except Exception:
            return None, None, None

        match = _INDEXED_PART_RE.match(partname)
        if not match:
            return None, partname, None

        folder = match.group("folder")
        index = match.group("index")
        label_prefix = "Chart" if folder == "word/charts" else "Embedding"
        label = f"{label_prefix} #{index}"

        return label, partname, folder

    def _log_indexed_part_start(self, label: str | None, partname: str | None) -> None:
        if not label and not partname:
            return
        logger.info('Templating "%s"', label or partname)

    def _log_template_statements(
        self,
        label: str | None,
        partname: str | None,
        xml: str,
        *,
        subpart: str | None = None,
    ) -> None:
        statements, total = self._collect_template_statements(xml, limit=20)
        if not statements:
            return

        scope = label or partname or "<unknown part>"
        prefix = f'"{scope}"'
        if subpart:
            prefix = f'{prefix} ({subpart})'

        logger.info(
            "Found %s templating statement%s in %s",
            total,
            "s" if total != 1 else "",
            prefix,
            extra={
                "docx_template_part": partname,
                "docx_template_label": label,
                "docx_template_statement_count": total,
                "docx_template_statements_preview": statements,
            },
        )

        for entry in statements:
            statement = entry.get("statement", "")
            line = entry.get("line")
            context_before = entry.get("before")
            context_after = entry.get("after")
            context_detail = []
            if context_before:
                context_detail.append(f"before: {context_before}")
            if context_after:
                context_detail.append(f"after: {context_after}")
            context_suffix = f" ({'; '.join(context_detail)})" if context_detail else ""

            logger.info(
                "Processing pattern %r in %s%s",
                statement,
                prefix,
                f" on line {line}{context_suffix}" if line else context_suffix,
                extra={
                    "docx_template_part": partname,
                    "docx_template_label": label,
                    "docx_template_statement": statement,
                    "docx_template_statement_line": line,
                    "docx_template_statement_context_before": context_before,
                    "docx_template_statement_context_after": context_after,
                    **({"docx_template_subpart": subpart} if subpart else {}),
                },
            )

    def _record_templated_part(self, bucket: str, label: str) -> None:
        if not hasattr(self, "_templated_part_labels"):
            self._templated_part_labels = defaultdict(list)
        self._templated_part_labels[bucket].append(label)

    def _summarise_templated_parts(self) -> None:
        labels: dict[str, list[str]] = getattr(self, "_templated_part_labels", {})
        if not labels:
            return

        embeddings = labels.get("embeddings", [])
        charts = labels.get("charts", [])
        if embeddings or charts:
            logger.info(
                "Templated %s embedding(s) and %s chart(s)",
                len(embeddings),
                len(charts),
                extra={
                    "docx_template_embeddings": embeddings,
                    "docx_template_charts": charts,
                },
            )

        if embeddings and charts and len(embeddings) != len(charts):
            logger.warning(
                "Templated embedding/chart counts differ; charts may reference shared or additional workbooks",
                extra={
                    "docx_template_embeddings": embeddings,
                    "docx_template_charts": charts,
                    "docx_template_count_delta": len(charts) - len(embeddings),
                },
            )

        if hasattr(self, "_templated_part_labels"):
            self._templated_part_labels.clear()

    def _log_indexed_part_error(
        self,
        label: str | None,
        partname: str | None,
        exc: Exception,
        *,
        xml: str | None = None,
        subpart: str | None = None,
    ) -> None:
        error_line = self._extract_template_error_line(exc)
        context_line, error_context = self._extract_template_debug_context(exc)
        if error_line is None and context_line is not None:
            error_line = context_line

        statements: list[dict[str, str | int]] = []
        total_statements = 0
        if xml is not None:
            statements, total_statements = self._collect_template_statements(
                xml, focus_line=error_line
            )
        preview_summary = (
            self._format_statement_preview(statements, total_statements)
            if xml is not None
            else None
        )
        context_summary = (
            self._format_template_context(error_context, error_line)
            if error_context
            else None
        )

        message_parts: list[str] = []
        if subpart:
            message_parts.append(subpart)
        if error_line is not None:
            message_parts.append(f"near template line {error_line}")
        if context_summary:
            message_parts.append(context_summary)
        if preview_summary:
            message_parts.append(preview_summary)
        message_parts.append(str(exc))
        detail = "; ".join(part for part in message_parts if part)

        logger.exception(
            'Error templating "%s"%s: %s',
            label or partname or "<unknown part>",
            f" ({partname})" if partname and label != partname else "",
            detail,
            extra={
                "docx_template_part": partname,
                "docx_template_label": label,
                "docx_template_error_line": error_line,
                **(
                    {
                        "docx_template_error_context": [
                            {"line": line, "text": text}
                            for line, text in (error_context or [])
                        ],
                        "docx_template_statements_preview": statements,
                        "docx_template_statement_count": total_statements,
                    }
                    if error_context or xml is not None
                    else {}
                ),
            },
        )

    def _is_excel_part(self, partname: str) -> bool:
        return partname.endswith(".xlsx")

    def _is_settings_part(self, part) -> bool:
        try:
            partname = self._normalise_partname(part)
        except Exception:
            return False
        return partname == _SETTINGS_PARTNAME

    def _render_additional_parts(self, context, jinja_env) -> None:
        parts = list(self._iter_additional_parts())
        excel_values: dict[str, dict[str, dict[str, str]]] = {}
        self._templated_part_labels = defaultdict(list)

        for part in parts:
            partname = self._normalise_partname(part)
            if not self._is_excel_part(partname):
                continue

            label, _described_partname, folder = self._describe_indexed_part(part)
            if folder == "word/embeddings":
                self._log_indexed_part_start(label, partname)

            try:
                rendered = self._render_excel_part(part, context, jinja_env)
            except Exception as exc:
                if folder == "word/embeddings":
                    self._log_indexed_part_error(label, partname, exc)
                raise
            if rendered is None:
                continue

            rendered_blob, workbook_values = rendered
            if rendered_blob is not None and hasattr(part, "_blob"):
                part._blob = rendered_blob
            if workbook_values:
                excel_values[partname] = workbook_values
            if folder == "word/embeddings" and label:
                self._record_templated_part("embeddings", label)

        for part in parts:
            partname = self._normalise_partname(part)
            if self._is_excel_part(partname):
                continue

            label, _described_partname, folder = self._describe_indexed_part(part)
            chart_label = label if folder == "word/charts" else None

            if chart_label:
                self._log_indexed_part_start(chart_label, partname)

            xml = self.get_part_xml(part)
            patched = self.patch_xml(xml)
            if chart_label:
                self._log_template_statements(chart_label, partname, patched)
            try:
                rendered = self.render_xml_part(patched, part, context, jinja_env)
            except Exception as exc:
                if chart_label:
                    self._log_indexed_part_error(chart_label, partname, exc, xml=patched)
                raise
            if chart_label:
                self._record_templated_part("charts", chart_label)

            if self._is_chart_part(partname):
                rendered = self._sync_chart_cache(rendered, part, excel_values)

                rendered_bytes = rendered.encode("utf-8")
                if hasattr(part, "_element"):
                    part._element = parse_xml(rendered_bytes)
                if hasattr(part, "_blob"):
                    part._blob = rendered_bytes
            else:
                rendered_bytes = rendered.encode("utf-8")
                if hasattr(part, "_element"):
                    part._element = parse_xml(rendered_bytes)
                if hasattr(part, "_blob"):
                    part._blob = rendered_bytes
            self._cleanup_part_relationships(part, rendered)

        self._summarise_templated_parts()

    def _renumber_media_parts(self) -> None:
        """Ensure chart and embedding parts are sequentially numbered."""

        parts = self._iter_package_parts()
        if not parts:
            return

        buckets: dict[tuple[str, str, str], list[tuple[int, object, str]]] = defaultdict(list)

        for part in parts:
            try:
                partname = self._normalise_partname(part)
            except Exception:
                continue

            match = _INDEXED_PART_RE.match(partname)
            if not match:
                continue

            try:
                index = int(match.group("index"))
            except (TypeError, ValueError):
                continue

            key = (match.group("folder"), match.group("prefix"), match.group("suffix"))
            buckets[key].append((index, part, partname))

        if not buckets:
            return

        renames: list[tuple[object, str, str]] = []

        for (folder, prefix, suffix), entries in buckets.items():
            entries.sort(key=lambda entry: entry[0])
            if all(index == position + 1 for position, (index, _part, _name) in enumerate(entries)):
                continue

            for position, (_index, part, current_name) in enumerate(entries, start=1):
                new_name = f"{folder}/{prefix}{position}{suffix}"
                if current_name == new_name:
                    continue
                renames.append((part, current_name, new_name))

        if not renames:
            return

        for part, old_name, new_name in renames:
            self._rename_part(part, old_name, new_name)

        self._update_relationship_targets(renames)

    def _cleanup_settings_part(self) -> None:
        doc = getattr(self, "docx", None)
        main_part = getattr(doc, "_part", None) if doc is not None else None
        if main_part is None:
            return

        try:
            settings_part = main_part.part_related_by(f"{_RELATIONSHIP_NS}/settings")
        except Exception:
            return

        raw_xml = self.get_part_xml(settings_part)
        if isinstance(raw_xml, bytes):
            xml_text = raw_xml.decode("utf-8")
        else:
            xml_text = raw_xml

        cleaned = self._cleanup_word_markup(settings_part, xml_text)

        if isinstance(cleaned, bytes):
            cleaned_bytes = cleaned
            cleaned_xml = cleaned.decode("utf-8", errors="ignore")
            parsed_root = parse_xml(cleaned_bytes)
        elif isinstance(cleaned, str):
            cleaned_xml = cleaned
            cleaned_bytes = cleaned.encode("utf-8")
            parsed_root = parse_xml(cleaned_bytes)
        else:
            parsed_root = self._ensure_xml_root(cleaned)
            if parsed_root is None:
                return
            cleaned_bytes = etree.tostring(parsed_root)
            cleaned_xml = cleaned_bytes.decode("utf-8", errors="ignore")

        if hasattr(settings_part, "_element"):
            settings_part._element = parsed_root
        if hasattr(settings_part, "_blob"):
            settings_part._blob = cleaned_bytes

        self._cleanup_part_relationships(settings_part, cleaned_xml)

    def _cleanup_comments_part(self) -> None:
        referenced = getattr(self, "_referenced_comment_ids", None)
        if referenced is None:
            return

        doc = getattr(self, "docx", None)
        main_part = getattr(doc, "_part", None) if doc is not None else None
        if main_part is None:
            return

        try:
            comments_part = main_part.part_related_by(f"{_RELATIONSHIP_NS}/comments")
        except Exception:
            return

        try:
            xml = self.get_part_xml(comments_part)
        except Exception:
            return

        root = self._ensure_xml_root(xml)
        if root is None:
            return

        word_ns = self._get_word_namespace(root)
        comment_tag = f"{{{word_ns}}}comment"
        id_attr = f"{{{word_ns}}}id"
        updated = False

        for comment in list(root.findall(comment_tag)):
            comment_id = comment.get(id_attr)
            if comment_id is None or str(comment_id) in referenced:
                continue
            self._remove_element(comment)
            updated = True

        if not updated:
            return

        cleaned = self._coerce_cleaned_xml(xml, root)

        if isinstance(cleaned, bytes):
            blob = cleaned
        elif isinstance(cleaned, str):
            blob = cleaned.encode("utf-8")
        else:
            blob = etree.tostring(cleaned)

        element = parse_xml(blob)

        if hasattr(comments_part, "_element"):
            comments_part._element = element
        if hasattr(comments_part, "_blob"):
            comments_part._blob = blob

    def _cleanup_part_relationships(self, part, xml) -> None:
        """Remove relationships not referenced in the rendered ``xml``."""

        rels = getattr(part, "rels", None)
        if not rels:
            return

        referenced = self._collect_relationship_ids(xml)
        required_types = self._get_required_relationship_types(part)
        if not referenced and not len(rels):
            return

        for rel_id, rel in list(rels.items()):
            if rel_id in referenced:
                continue
            reltype = getattr(rel, "reltype", "")
            if reltype in required_types:
                continue
            if self._try_drop_relationship(part, rel_id):
                continue
            self._remove_relationship_entry(rels, rel_id)

        if self._is_document_part(part):
            self._ensure_modern_comments_relationship(rels)

    def _rename_part(self, part, old_name: str, new_name: str) -> None:
        """Rename ``part`` within the OPC package to ``new_name``."""

        try:
            old_pack_uri = getattr(part, "partname", None)
        except Exception:
            old_pack_uri = None

        old_normalised = old_name.lstrip("/")
        if old_pack_uri is not None:
            old_pack_uri_str = str(old_pack_uri).lstrip("/")
        else:
            old_pack_uri_str = old_normalised

        try:
            new_pack_uri = PackURI(f"/{new_name}")
        except Exception:
            return

        package = getattr(part, "package", None) or self._resolve_package()

        if package is not None:
            self._update_package_mappings(
                package, old_pack_uri, old_pack_uri_str, new_pack_uri, part
            )

        for attr in ("_partname", "partname"):
            if hasattr(part, attr):
                try:
                    setattr(part, attr, new_pack_uri)
                except Exception:
                    pass

    def _resolve_package(self):
        doc = getattr(self, "docx", None)
        main_part = getattr(doc, "_part", None) if doc is not None else None
        return getattr(main_part, "package", None) if main_part is not None else None

    def _update_package_mappings(
        self,
        package,
        old_pack_uri,
        old_name: str | None,
        new_pack_uri,
        part,
    ) -> None:
        mappings = [
            getattr(package, "_parts", None),
            getattr(package, "_partnames", None),
        ]

        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            if old_pack_uri in mapping:
                mapping.pop(old_pack_uri, None)
            elif old_name is not None:
                for key in list(mapping.keys()):
                    if str(key).lstrip("/") == old_name:
                        mapping.pop(key, None)
            mapping[new_pack_uri] = part

        content_types = getattr(package, "_content_types", None)
        if content_types is None:
            content_types = getattr(package, "content_types", None)

        overrides = getattr(content_types, "_overrides", None) if content_types else None
        if isinstance(overrides, dict):
            if old_pack_uri in overrides:
                overrides[new_pack_uri] = overrides.pop(old_pack_uri)
            elif old_name is not None:
                for key in list(overrides.keys()):
                    if str(key).lstrip("/") == old_name:
                        overrides[new_pack_uri] = overrides.pop(key)
                        break

    def _update_relationship_targets(
        self, renames: list[tuple[object, str, str]]
    ) -> None:
        if not renames:
            return

        lookup = {part: new_name for part, _old, new_name in renames}

        for source_part in self._iter_package_parts():
            rels = getattr(source_part, "rels", None)
            if not rels:
                continue

            try:
                source_name = self._normalise_partname(source_part)
            except Exception:
                continue

            for rel in list(getattr(rels, "values", lambda: [])()):
                try:
                    target_part = getattr(rel, "target_part", None)
                except ValueError:
                    # External relationships do not expose a ``target_part``;
                    # they reference an absolute target and are unaffected by
                    # part renames within the package.
                    continue
                if target_part not in lookup:
                    continue
                absolute_target = lookup[target_part]
                relative_target = self._build_relationship_target(
                    source_name, absolute_target
                )
                self._set_relationship_target(rel, relative_target, target_part)

                targets_map = getattr(rels, "_target_parts_by_rId", None)
                if isinstance(targets_map, dict):
                    targets_map[rel.rId] = target_part

    def _build_relationship_target(self, source_name: str, target_name: str) -> str:
        source_dir = posixpath.dirname(source_name) or "."
        relative = posixpath.relpath(target_name, source_dir).replace("\\", "/")
        if relative == ".":
            return posixpath.basename(target_name)
        return relative

    def _set_relationship_target(
        self, rel, relative_target: str, target_part
    ) -> None:
        for attr in ("target_ref", "_target_ref"):
            if hasattr(rel, attr):
                try:
                    setattr(rel, attr, relative_target)
                except Exception:
                    pass

        if hasattr(rel, "_target") and not getattr(rel, "is_external", False):
            try:
                rel._target = target_part
            except Exception:
                pass

    def _try_drop_relationship(self, part, rel_id: str) -> bool:
        """Attempt to drop relationship via the part API, returning ``True`` if removed."""

        drop_rel = getattr(part, "drop_rel", None)
        if not callable(drop_rel):
            return False

        rels = getattr(part, "rels", None)

        try:
            drop_rel(rel_id)
        except KeyError:
            removed = True
        except Exception:
            return False
        else:
            removed = rel_id not in rels if rels else True

        if not removed:
            return False

        targets = getattr(rels, "_target_parts_by_rId", None) if rels is not None else None
        if targets is not None:
            targets.pop(rel_id, None)

        return True

    def render_xml_part(self, xml, part, context, jinja_env):  # type: ignore[override]
        """Render ``xml`` for ``part`` and log detailed failures."""

        try:
            return super().render_xml_part(xml, part, context, jinja_env)
        except Exception as exc:
            part_label = self._describe_part(part)
            error_line = self._extract_template_error_line(exc)
            context_line, error_context = self._extract_template_debug_context(exc)
            if error_line is None and context_line is not None:
                error_line = context_line
            statements, total = self._collect_template_statements(
                xml, focus_line=error_line
            )
            preview_summary = self._format_statement_preview(statements, total)
            message_parts: list[str] = []
            if error_line is not None:
                message_parts.append(f"error near template line {error_line}")
            if error_context:
                message_parts.append(
                    self._format_template_context(error_context, error_line)
                )
            message_parts.append(preview_summary)
            message_detail = "; ".join(message_parts)
            logger.exception(
                "Failed to render DOCX template part %s. %s",
                part_label,
                message_detail,
                extra={
                    "docx_template_part": part_label,
                    "docx_template_statement_count": total,
                    "docx_template_statements_preview": statements,
                    "docx_template_error_line": error_line,
                    **(
                        {
                            "docx_template_error_context": [
                                {"line": line, "text": text}
                                for line, text in error_context
                            ]
                        }
                        if error_context
                        else {}
                    ),
                },
            )
            raise

    def _describe_part(self, part) -> str:
        if part is None:
            return "<document>"
        partname = getattr(part, "partname", None)
        if partname:
            return str(partname).lstrip("/") or "<document>"
        reltype = getattr(part, "reltype", None)
        if reltype:
            return f"<{reltype}>"
        return "<unknown>"

    def _collect_template_statements(
        self, xml: str, limit: int = 10, *, focus_line: int | None = None
    ) -> tuple[list[dict[str, str | int]], int]:
        """Return a preview of templating statements found in ``xml``."""

        preview: list[dict[str, str | int]] = []
        total = 0
        matches: list[tuple[int, str, int]] = []

        for match in _JINJA_STATEMENT_RE.finditer(xml):
            total += 1
            start = match.start()
            line = xml.count("\n", 0, start) + 1
            snippet = match.group(0)
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."

            matches.append((line, snippet, start))

        if not matches:
            return [], total

        selected: list[tuple[int, str, int]]
        if focus_line is not None:
            focus_index: int | None = None
            for index, (line, _snippet, _start) in enumerate(matches):
                if line >= focus_line:
                    focus_index = index
                    break
            if focus_index is None:
                start_index = max(0, len(matches) - limit)
            else:
                start_index = focus_index - (limit // 2)
                if start_index < 0:
                    start_index = 0
                if start_index + limit > len(matches):
                    start_index = max(0, len(matches) - limit)
            selected = matches[start_index : start_index + limit]
        else:
            selected = matches[:limit]

        for line, snippet, start in selected:
            entry: dict[str, str | int] = {"line": line, "statement": snippet}
            context = self._build_statement_context(xml, start)
            if context:
                entry.update(context)
            preview.append(entry)

        return preview, total

    def _extract_template_error_line(self, exc: BaseException) -> int | None:
        """Return the line number within the Jinja template that raised ``exc``."""

        tb = exc.__traceback__
        last_line: int | None = None

        while tb is not None:
            frame = tb.tb_frame
            if frame.f_code.co_filename == "<template>":
                last_line = tb.tb_lineno
            tb = tb.tb_next

        return last_line

    def _extract_template_debug_context(
        self,
        exc: BaseException,
        *,
        before: int = 2,
        after: int = 2,
    ) -> tuple[int | None, list[tuple[int, str]]]:
        """Return contextual template lines surrounding the error."""

        if JinjaTraceback is None:
            return None, []

        try:
            traceback = JinjaTraceback.from_exception(exc)
        except Exception:
            return None, []

        context_line: int | None = None
        context: list[tuple[int, str]] = []

        for frame in traceback.frames:
            filename = getattr(frame, "filename", getattr(frame, "name", None))
            if filename != "<template>":
                continue

            context_line = getattr(frame, "lineno", None)
            source = getattr(frame, "source", None)
            if not source:
                break

            lines = source.splitlines()
            if context_line is None:
                break

            start = max(context_line - 1 - before, 0)
            end = min(context_line - 1 + after + 1, len(lines))

            for index in range(start, end):
                line_text = self._trim_template_text(lines[index])
                context.append((index + 1, line_text))
            break

        return context_line, context

    def _format_statement_preview(
        self, statements: list[dict[str, str | int]], total: int
    ) -> str:
        """Summarise templating statements for logging."""

        if not statements:
            if total:
                return (
                    "Collected %d templating statements but preview is limited to 0 entries."
                    % total
                )
            return "No templating statements were found in the templated XML."

        formatted_entries: list[str] = []
        for entry in statements:
            parts: list[str] = []

            line = entry.get("line")
            if isinstance(line, int):
                parts.append(f"line {line}")

            statement = entry.get("statement")
            if isinstance(statement, str):
                parts.append(f"statement={statement!r}")

            paragraph = entry.get("paragraph_index")
            if isinstance(paragraph, int):
                parts.append(f"paragraph {paragraph}")

            paragraph_text = entry.get("paragraph_text")
            if isinstance(paragraph_text, str) and paragraph_text:
                parts.append(f"text={paragraph_text!r}")

            table = entry.get("table_index")
            if isinstance(table, int):
                table_parts = [f"table {table}"]
                row = entry.get("table_row_index")
                if isinstance(row, int):
                    table_parts.append(f"row {row}")
                cell = entry.get("table_cell_index")
                if isinstance(cell, int):
                    table_parts.append(f"cell {cell}")
                parts.append(", ".join(table_parts))

            formatted_entries.append("; ".join(parts))

        if len(statements) < total:
            formatted_entries.append(
                f"…and {total - len(statements)} more templating statements not shown"
            )

        return " | ".join(formatted_entries)

    def _format_template_context(
        self, context_lines: list[tuple[int, str]], error_line: int | None
    ) -> str:
        """Format template source context for inclusion in log messages."""

        if not context_lines:
            return ""

        formatted: list[str] = []
        for line_number, text in context_lines:
            label = f"line {line_number}"
            if error_line is not None and line_number == error_line:
                label += " (error)"
            formatted.append(f"{label}={text!r}")

        return "template context: " + " | ".join(formatted)

    def _build_statement_context(self, xml: str, start: int) -> dict[str, str | int]:
        """Return Word-specific context for a templating statement."""

        context: dict[str, str | int] = {}

        paragraph_context = self._locate_paragraph_context(xml, start)
        if paragraph_context:
            context.update(paragraph_context)

        table_context = self._locate_table_context(xml, start)
        if table_context:
            context.update(table_context)

        return context

    def _locate_paragraph_context(self, xml: str, start: int) -> dict[str, str | int]:
        """Return paragraph index/text surrounding ``start`` in Word XML."""

        before = xml[:start]
        paragraph_matches = list(re.finditer(r"<w:p\b", before))
        if not paragraph_matches:
            return {}

        paragraph_index = len(paragraph_matches)
        paragraph_start = paragraph_matches[-1].start()
        paragraph_end = xml.find("</w:p>", start)
        if paragraph_end == -1:
            paragraph_end = start

        paragraph_xml = xml[paragraph_start:paragraph_end]
        paragraph_text = self._strip_word_text(paragraph_xml)

        context: dict[str, str | int] = {"paragraph_index": paragraph_index}
        if paragraph_text:
            context["paragraph_text"] = paragraph_text

        return context

    def _locate_table_context(self, xml: str, start: int) -> dict[str, str | int]:
        """Return table indices surrounding ``start`` in Word XML."""

        before = xml[:start]
        table_matches = list(re.finditer(r"<w:tbl\b", before))
        if not table_matches:
            return {}

        context: dict[str, str | int] = {"table_index": len(table_matches)}

        table_start = table_matches[-1].start()
        table_slice = xml[table_start:start]

        row_matches = list(re.finditer(r"<w:tr\b", table_slice))
        if row_matches:
            context["table_row_index"] = len(row_matches)
            row_start = table_start + row_matches[-1].start()
            row_slice = xml[row_start:start]
            cell_matches = list(re.finditer(r"<w:tc\b", row_slice))
            if cell_matches:
                context["table_cell_index"] = len(cell_matches)

        return context

    def _strip_word_text(self, xml_snippet: str) -> str:
        """Return simplified paragraph text for a WordprocessingML snippet."""

        if not xml_snippet:
            return ""

        text = re.sub(r"<[^>]+>", " ", xml_snippet)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 200:
            return text[:197] + "..."
        return text

    def _trim_template_text(self, text: str) -> str:
        """Normalise whitespace and length for template context lines."""

        cleaned = text.strip("\r\n")
        if len(cleaned) > 200:
            return cleaned[:197] + "..."
        return cleaned

    def _remove_relationship_entry(self, rels, rel_id: str) -> None:
        """Remove relationship ``rel_id`` from ``rels`` and any cached target maps."""

        if rels is None:
            return

        rels.pop(rel_id, None)
        targets = getattr(rels, "_target_parts_by_rId", None)
        if targets is not None:
            targets.pop(rel_id, None)

    def _get_required_relationship_types(self, part) -> set[str]:
        partname = getattr(part, "partname", None)
        if not partname:
            return set()

        normalised = str(partname).lstrip("/")
        if normalised == _DOCUMENT_PARTNAME:
            return set(self._DOCUMENT_REQUIRED_RELATIONSHIP_TYPES)
        return set()

    def _cleanup_word_markup(self, part, xml):
        """Normalise WordprocessingML after templating removes content."""

        root = self._ensure_xml_root(xml)
        if root is None:
            return xml

        word_ns = self._get_word_namespace(root)

        self._remove_unbalanced_bookmarks(root, word_ns)
        self._remove_unbalanced_range_elements(
            root,
            word_ns,
            (
                ("commentRangeStart", "commentRangeEnd"),
                ("moveFromRangeStart", "moveFromRangeEnd"),
                ("moveToRangeStart", "moveToRangeEnd"),
                ("customXmlDelRangeStart", "customXmlDelRangeEnd"),
                ("customXmlInsRangeStart", "customXmlInsRangeEnd"),
                (
                    "customXmlMoveFromRangeStart",
                    "customXmlMoveFromRangeEnd",
                ),
                ("customXmlMoveToRangeStart", "customXmlMoveToRangeEnd"),
                ("permStart", "permEnd"),
            ),
        )
        bookmark_names = self._collect_bookmark_names(root, word_ns)
        self._remove_missing_anchor_hyperlinks(root, word_ns, bookmark_names)
        self._remove_missing_bookmark_fields(root, word_ns, bookmark_names)
        if part is not None:
            if self._is_settings_part(part):
                self._remove_attached_template(part, root, word_ns)
            self._remove_external_file_hyperlinks(part, root, word_ns)

        self._ensure_unique_paragraph_ids(root, word_ns)
        self._record_comment_references(root, word_ns)

        return self._coerce_cleaned_xml(xml, root)

    def _get_namespace(self, root, prefix: str, default: str | None = None) -> str | None:
        if hasattr(root, "nsmap") and root.nsmap:
            namespace = root.nsmap.get(prefix)
            if namespace:
                return namespace
        return default

    def _get_word_namespace(self, root) -> str:
        namespace = self._get_namespace(root, "w", _WORDPROCESSING_NS)
        return namespace or _WORDPROCESSING_NS

    def _ensure_unique_paragraph_ids(self, root, word_ns: str) -> None:
        w14_ns = self._get_namespace(root, "w14", _WORD2010_NS)
        if not w14_ns:
            return

        para_tag = f"{{{word_ns}}}p"
        para_attr = f"{{{w14_ns}}}paraId"

        paragraphs = list(root.iter(para_tag))
        if not paragraphs:
            return

        removed = False
        for paragraph in paragraphs:
            if paragraph.get(para_attr) is not None:
                paragraph.attrib.pop(para_attr, None)
                removed = True

        if removed:
            logger = logging.getLogger(__name__)
            logger.debug("Stripped w14:paraId attributes from %s paragraphs", len(paragraphs))

    def _remove_unbalanced_bookmarks(self, root, word_ns: str) -> None:
        start_tag = f"{{{word_ns}}}bookmarkStart"
        end_tag = f"{{{word_ns}}}bookmarkEnd"
        id_attr = f"{{{word_ns}}}id"
        name_attr = f"{{{word_ns}}}name"

        starts: dict[str, list] = defaultdict(list)
        ends: dict[str, list] = defaultdict(list)
        duplicate_ids: set[str] = set()
        seen_names: set[str] = set()

        for element in root.iter():
            if element.tag == start_tag:
                bookmark_id = element.get(id_attr)
                if bookmark_id is not None:
                    bookmark_key = str(bookmark_id)
                    starts[bookmark_key].append(element)
                    name = element.get(name_attr)
                    if name == "_GoBack":
                        continue
                    normalised = self._normalise_bookmark_name(name)
                    if normalised is None or normalised in seen_names:
                        duplicate_ids.add(bookmark_key)
                    else:
                        seen_names.add(normalised)
            elif element.tag == end_tag:
                bookmark_id = element.get(id_attr)
                if bookmark_id is not None:
                    ends[str(bookmark_id)].append(element)

        start_ids = set(starts)
        end_ids = set(ends)

        for bookmark_id in start_ids - end_ids:
            for element in starts[bookmark_id]:
                self._remove_element(element)

        for bookmark_id in end_ids - start_ids:
            for element in ends[bookmark_id]:
                self._remove_element(element)

        for bookmark_id in start_ids & end_ids:
            start_elements = starts[bookmark_id]
            end_elements = ends[bookmark_id]
            pair_count = min(len(start_elements), len(end_elements))
            for element in start_elements[pair_count:]:
                self._remove_element(element)
            for element in end_elements[pair_count:]:
                self._remove_element(element)

        for bookmark_id in duplicate_ids:
            for element in starts.get(bookmark_id, []):
                self._remove_element(element)
            for element in ends.get(bookmark_id, []):
                self._remove_element(element)

    def _collect_bookmark_names(self, root, word_ns: str) -> set[str]:
        start_tag = f"{{{word_ns}}}bookmarkStart"
        name_attr = f"{{{word_ns}}}name"
        names: set[str] = set()

        for element in root.iter(start_tag):
            name = element.get(name_attr)
            if name == "_GoBack":
                continue
            normalised = self._normalise_bookmark_name(name)
            if normalised:
                names.add(normalised)

        return names

    def _record_comment_references(self, root, word_ns: str) -> None:
        referenced = getattr(self, "_referenced_comment_ids", None)
        if referenced is None:
            referenced = set()
            self._referenced_comment_ids = referenced

        id_attr = f"{{{word_ns}}}id"
        tags = (
            f"{{{word_ns}}}commentRangeStart",
            f"{{{word_ns}}}commentRangeEnd",
            f"{{{word_ns}}}commentReference",
        )

        for tag in tags:
            for element in root.iter(tag):
                comment_id = element.get(id_attr)
                if comment_id is not None:
                    referenced.add(str(comment_id))

    def _remove_unbalanced_range_elements(
        self,
        root,
        word_ns: str,
        pairs: tuple[tuple[str, str], ...],
    ) -> None:
        id_attr = f"{{{word_ns}}}id"

        for start_local, end_local in pairs:
            start_tag = f"{{{word_ns}}}{start_local}"
            end_tag = f"{{{word_ns}}}{end_local}"

            starts: dict[str, list] = defaultdict(list)
            ends: dict[str, list] = defaultdict(list)

            for element in root.iter(start_tag):
                marker_id = element.get(id_attr)
                if marker_id is not None:
                    starts[str(marker_id)].append(element)

            for element in root.iter(end_tag):
                marker_id = element.get(id_attr)
                if marker_id is not None:
                    ends[str(marker_id)].append(element)

            start_ids = set(starts)
            end_ids = set(ends)

            for marker_id in start_ids - end_ids:
                for element in starts[marker_id]:
                    self._remove_element(element)

            for marker_id in end_ids - start_ids:
                for element in ends[marker_id]:
                    self._remove_element(element)

            for marker_id in start_ids & end_ids:
                start_elements = starts[marker_id]
                end_elements = ends[marker_id]
                pair_count = min(len(start_elements), len(end_elements))

                for element in start_elements[pair_count:]:
                    self._remove_element(element)
                for element in end_elements[pair_count:]:
                    self._remove_element(element)

    def _remove_missing_anchor_hyperlinks(
        self,
        root,
        word_ns: str,
        bookmark_names: set[str],
    ) -> None:
        hyperlink_tag = f"{{{word_ns}}}hyperlink"
        anchor_attr = f"{{{word_ns}}}anchor"

        for hyperlink in list(root.iter(hyperlink_tag)):
            anchor = hyperlink.get(anchor_attr)
            normalised = self._normalise_bookmark_name(anchor)
            if normalised and normalised in bookmark_names:
                continue
            self._unwrap_element(hyperlink)

    def _remove_missing_bookmark_fields(
        self,
        root,
        word_ns: str,
        bookmark_names: set[str],
    ) -> None:
        fld_simple_tag = f"{{{word_ns}}}fldSimple"
        instr_attr = f"{{{word_ns}}}instr"

        for field in list(root.iter(fld_simple_tag)):
            instr = field.get(instr_attr, "")
            if self._field_references_missing_bookmark(instr, bookmark_names):
                self._remove_element(field)

        fld_char_tag = f"{{{word_ns}}}fldChar"
        fld_char_type_attr = f"{{{word_ns}}}fldCharType"
        instr_text_tag = f"{{{word_ns}}}instrText"
        run_tag = f"{{{word_ns}}}r"

        runs_to_remove: set[object] = set()
        field_state: dict[str, object] | None = None

        for element in root.iter():
            if element.tag == fld_char_tag:
                fld_type = element.get(fld_char_type_attr)
                if fld_type == "begin":
                    field_state = {
                        "instr_parts": [],
                        "runs": set(),
                        "remove": False,
                    }
                if field_state is not None:
                    run = self._find_ancestor(element, run_tag)
                    if run is not None:
                        field_state["runs"].add(run)
                    if fld_type == "end":
                        if field_state["remove"]:
                            runs_to_remove.update(field_state["runs"])
                        field_state = None
                continue

            if field_state is None:
                continue

            run = self._find_ancestor(element, run_tag)
            if run is not None:
                field_state["runs"].add(run)

            if element.tag != instr_text_tag:
                continue

            text = element.text or ""
            if not text:
                continue

            field_state["instr_parts"].append(text)
            if field_state["remove"]:
                continue

            instr_text = "".join(field_state["instr_parts"])
            if self._field_references_missing_bookmark(instr_text, bookmark_names):
                field_state["remove"] = True

        for run in runs_to_remove:
            self._remove_element(run)

    def _field_references_missing_bookmark(
        self,
        instruction: str,
        bookmark_names: set[str],
    ) -> bool:
        if not instruction:
            return False

        candidates: set[str] = set()

        for match in _BOOKMARK_FIELD_RE.finditer(instruction):
            name = match.group(1) or match.group(2)
            if name:
                candidates.add(name)

        for match in _BOOKMARK_HYPERLINK_FIELD_RE.finditer(instruction):
            name = match.group(1)
            if name:
                candidates.add(name)

        if not candidates:
            return False

        for name in candidates:
            normalised = self._normalise_bookmark_name(name)
            if not normalised or normalised not in bookmark_names:
                return True
        return False

    def _find_ancestor(self, element, tag: str):
        current = element
        while current is not None:
            if current.tag == tag:
                return current
            current = current.getparent() if hasattr(current, "getparent") else None
        return None

    def _normalise_bookmark_name(self, name: str | None) -> str | None:
        if not name:
            return None

        cleaned = name.strip()
        if not cleaned:
            return None

        return cleaned.casefold()

    def _remove_attached_template(self, part, root, word_ns: str) -> None:
        if not self._is_settings_part(part):
            return

        attached_tag = f"{{{word_ns}}}attachedTemplate"
        rel_attr = f"{{{_RELATIONSHIP_NS}}}id"
        rels = getattr(part, "rels", None)

        for element in list(root.iter(attached_tag)):
            rel_id = element.get(rel_attr)
            self._remove_element(element)
            if rel_id and rels is not None:
                self._remove_relationship_entry(rels, rel_id)

    def _remove_external_file_hyperlinks(self, part, root, word_ns: str) -> None:
        rels = getattr(part, "rels", None)
        if not rels:
            return

        for rel_id, rel in list(rels.items()):
            reltype = getattr(rel, "reltype", "")
            is_external = getattr(rel, "is_external", False)
            if reltype != _HYPERLINK_RELTYPE or not is_external:
                continue

            target = self._get_relationship_target(rel)
            if not target or not target.lower().startswith("file:"):
                continue

            self._remove_hyperlink_elements_by_id(root, rel_id, word_ns)
            if hasattr(part, "drop_rel"):
                part.drop_rel(rel_id)
            else:
                rels.pop(rel_id, None)
            targets = getattr(rels, "_target_parts_by_rId", None)
            if targets is not None:
                targets.pop(rel_id, None)

    def _remove_hyperlink_elements_by_id(self, root, rel_id: str, word_ns: str) -> None:
        hyperlink_tag = f"{{{word_ns}}}hyperlink"
        rel_attr = f"{{{_RELATIONSHIP_NS}}}id"

        for hyperlink in list(root.iter(hyperlink_tag)):
            if hyperlink.get(rel_attr) != rel_id:
                continue
            self._unwrap_element(hyperlink)

    def _get_relationship_target(self, rel) -> str:
        for attr in ("target_ref", "target", "target_uri", "target_ref_uri"):
            value = getattr(rel, attr, None)
            if value:
                return str(value)
        return ""

    def _unwrap_element(self, element) -> None:
        parent = element.getparent()
        if parent is None:
            return

        index = parent.index(element)
        prev = parent[index - 1] if index > 0 else None

        for child in list(element):
            element.remove(child)
            parent.insert(index, child)
            index += 1

        tail = element.tail
        parent.remove(element)

        if tail:
            if index < len(parent):
                next_el = parent[index]
                next_el.tail = (tail + (next_el.tail or "")) if next_el.tail else tail
            elif prev is not None:
                prev.tail = (prev.tail or "") + tail
            else:
                parent.text = (parent.text or "") + tail

    def _remove_element(self, element) -> None:
        parent = element.getparent()
        if parent is None:
            return

        index = parent.index(element)
        tail = element.tail
        parent.remove(element)

        if tail:
            if index < len(parent):
                next_el = parent[index]
                next_el.tail = (tail + (next_el.tail or "")) if next_el.tail else tail
            else:
                previous = parent[index - 1] if index > 0 else None
                if previous is not None:
                    previous.tail = (previous.tail or "") + tail
                else:
                    parent.text = (parent.text or "") + tail

    def _coerce_cleaned_xml(self, original, root):
        if isinstance(original, etree._ElementTree):
            return original
        if isinstance(original, etree._Element):
            return root
        if isinstance(original, bytes):
            return etree.tostring(root)
        return etree.tostring(root, encoding="unicode")

    def _collect_relationship_ids(self, xml) -> set[str]:
        root = self._ensure_xml_root(xml)
        if root is None:
            return set()

        referenced: set[str] = set()
        for element in root.iter():
            for attr_name, attr_value in element.attrib.items():
                if not attr_name.startswith(_RELATIONSHIP_PREFIX):
                    continue
                referenced.update(self._parse_relationship_value(attr_value))
        return referenced

    def _ensure_xml_root(self, xml):
        if isinstance(xml, etree._Element):
            tree = xml.getroottree()
            return tree.getroot() if tree is not None else xml
        if isinstance(xml, etree._ElementTree):
            return xml.getroot()

        if isinstance(xml, bytes):
            data = xml
        elif isinstance(xml, str):
            data = xml.encode("utf-8")
        else:
            return None

        try:
            return etree.fromstring(data)
        except etree.XMLSyntaxError:
            return None

    def _parse_relationship_value(self, value: str) -> set[str]:
        if not value:
            return set()

        matches = re.findall(r"rId\d+", value)
        if matches:
            return set(matches)

        stripped = value.strip()
        if not stripped:
            return set()

        parts = stripped.split()
        if len(parts) > 1:
            matches = re.findall(r"rId\d+", " ".join(parts))
            if matches:
                return set(matches)
            return {part for part in parts if part}

        return {stripped}

    def _read_excel_part(self, part) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]] | None:
        blob = getattr(part, "_blob", None)
        if blob is None and hasattr(part, "blob"):
            blob = part.blob
        if not blob:
            return None

        source = io.BytesIO(blob)
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            files = {info.filename: archive.read(info.filename) for info in infos}
        return infos, files

    def _render_excel_part(self, part, context, jinja_env):
        infos_files = self._read_excel_part(part)
        if infos_files is None:
            return None
        infos, files = infos_files

        files = self._inline_templated_shared_strings(files)

        rendered_xml: dict[str, str] = {}
        label, part_label, folder = self._describe_indexed_part(part)
        for name, data in files.items():
            if not name.endswith(".xml"):
                continue
            xml = data.decode("utf-8")
            patched = self.patch_xml(xml)
            if folder == "word/embeddings":
                self._log_template_statements(label, part_label, patched, subpart=name)
            try:
                rendered_xml[name] = self.render_xml_part(
                    patched, part, context, jinja_env
                )
            except Exception as exc:
                if folder == "word/embeddings":
                    self._log_indexed_part_error(
                        label, part_label, exc, xml=patched, subpart=name
                    )
                raise

        sheet_map = self._build_sheet_map(rendered_xml, files)
        rendered_xml, workbook_values = self._coerce_excel_types(rendered_xml, sheet_map)
        rendered_xml, table_map = self._sync_excel_tables(
            rendered_xml,
            files,
            sheet_map,
            workbook_values,
        )
        if table_map:
            workbook_values.setdefault("__tables__", table_map)

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for info in infos:
                filename = info.filename
                data = rendered_xml.get(filename)
                if data is not None:
                    content: bytes = data.encode("utf-8")
                else:
                    content = files[filename]

                new_info = zipfile.ZipInfo(filename)
                new_info.date_time = info.date_time
                new_info.external_attr = info.external_attr
                new_info.internal_attr = info.internal_attr
                new_info.compress_type = info.compress_type
                new_info.flag_bits = info.flag_bits
                archive.writestr(new_info, content)

        return output.getvalue(), workbook_values

    def _inline_templated_shared_strings(self, files: dict[str, bytes]) -> dict[str, bytes]:
        """Embed templated shared strings directly in worksheet cells.

        Ghostwriter templates often place ``{{ ... }}`` and ``{% ... %}`` markers in
        shared string entries that are referenced from worksheet cells. When those
        entries participate in ``{%tr%}`` loops, the shared string is rendered
        outside of the loop context and raises ``UndefinedError`` exceptions. To
        avoid this, shared-string backed cells containing template statements are
        converted to inline strings and the shared string entries are cleared so
        the templating engine no longer sees the Ghostwriter markers.
        """

        shared_key = "xl/sharedStrings.xml"
        shared_blob = files.get(shared_key)
        if not shared_blob:
            return files

        try:
            shared_tree = etree.fromstring(shared_blob)
        except etree.XMLSyntaxError:
            return files

        shared_ns = shared_tree.nsmap.get(None)
        shared_prefix = f"{{{shared_ns}}}" if shared_ns else ""

        templated_entries: dict[int, etree._Element] = {}
        changed_shared = False
        for idx, si in enumerate(shared_tree.findall(f"{shared_prefix}si")):
            text = "".join(si.itertext())
            if not any(marker in text for marker in ("{{", "{%", "{#")):
                continue

            templated_entries[idx] = deepcopy(si)
            for child in list(si):
                si.remove(child)
            empty = etree.SubElement(si, f"{shared_prefix}t")
            empty.text = ""
            empty.attrib.pop("{http://www.w3.org/XML/1998/namespace}space", None)
            changed_shared = True

        if not templated_entries:
            return files

        if changed_shared:
            files[shared_key] = etree.tostring(shared_tree, encoding="utf-8")

        for name, blob in list(files.items()):
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue

            try:
                sheet_tree = etree.fromstring(blob)
            except etree.XMLSyntaxError:
                continue

            sheet_ns = sheet_tree.nsmap.get(None)
            sheet_prefix = f"{{{sheet_ns}}}" if sheet_ns else ""
            updated = False

            for cell in sheet_tree.findall(f".//{sheet_prefix}c[@t='s']"):
                value_node = cell.find(f"{sheet_prefix}v")
                if value_node is None or value_node.text is None:
                    continue

                try:
                    shared_index = int(value_node.text)
                except ValueError:
                    continue

                shared_value = templated_entries.get(shared_index)
                if shared_value is None:
                    continue

                for child in list(cell):
                    if etree.QName(child).localname in {"v", "is"}:
                        cell.remove(child)

                cell.set("t", "inlineStr")
                inline = etree.SubElement(cell, f"{sheet_prefix}is")
                for child in shared_value:
                    inline.append(deepcopy(child))
                updated = True

            if updated:
                files[name] = etree.tostring(sheet_tree, encoding="utf-8")

        return files

    def _is_chart_part(self, partname: str) -> bool:
        return partname.startswith("word/charts/") and partname.endswith(".xml")

    def _build_sheet_map(
        self,
        rendered_xml: dict[str, str],
        files: dict[str, bytes],
    ) -> dict[str, str]:
        workbook_xml = rendered_xml.get("xl/workbook.xml")
        if workbook_xml is None and "xl/workbook.xml" in files:
            workbook_xml = files["xl/workbook.xml"].decode("utf-8")

        rels_xml = rendered_xml.get("xl/_rels/workbook.xml.rels")
        if rels_xml is None and "xl/_rels/workbook.xml.rels" in files:
            rels_xml = files["xl/_rels/workbook.xml.rels"].decode("utf-8")

        if not workbook_xml or not rels_xml:
            return {}

        return self._parse_sheet_map(workbook_xml, rels_xml)

    def _parse_sheet_map(self, workbook_xml: str, rels_xml: str) -> dict[str, str]:
        try:
            workbook_tree = etree.fromstring(workbook_xml.encode("utf-8"))
            rels_tree = etree.fromstring(rels_xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return {}

        ns = workbook_tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""
        rels_ns = rels_tree.nsmap.get(None)
        rels_prefix = f"{{{rels_ns}}}" if rels_ns else ""
        r_ns = workbook_tree.nsmap.get("r")
        default_r_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        r_prefix = f"{{{r_ns}}}" if r_ns else f"{{{default_r_ns}}}"

        rel_targets: dict[str, str] = {}
        for rel in rels_tree.findall(f"{rels_prefix}Relationship"):
            rel_id = rel.get("Id")
            target = rel.get("Target")
            if not rel_id or not target:
                continue
            rel_targets[rel_id] = target

        sheet_map: dict[str, str] = {}
        for sheet in workbook_tree.findall(f".//{prefix}sheet"):
            name = sheet.get("name")
            rel_id = sheet.get(f"{r_prefix}id")
            if not name or not rel_id:
                continue
            target = rel_targets.get(rel_id)
            if not target:
                continue
            target_path = target.lstrip("/")
            if not target_path.startswith("xl/"):
                target_path = f"xl/{target_path}"
            sheet_map[target_path] = name

        return sheet_map

    # Excel helpers -------------------------------------------------

    def _coerce_excel_types(
        self,
        xml_files: dict[str, str],
        sheet_map: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
        if not xml_files:
            return xml_files, {}

        shared_strings = None
        shared_strings_key = "xl/sharedStrings.xml"
        if shared_strings_key in xml_files:
            shared_strings = self._parse_shared_strings(xml_files[shared_strings_key])

        workbook_values: dict[str, dict[str, str]] = {}
        for name, xml in list(xml_files.items()):
            if not name.startswith("xl/worksheets/"):
                continue
            normalised = self._normalise_sheet_rows(xml)
            if normalised != xml:
                xml_files[name] = normalised
                xml = normalised

            sheet_name = sheet_map.get(name)
            coerced, cell_values = self._coerce_sheet_types(
                xml,
                shared_strings,
            )
            xml_files[name] = coerced
            if cell_values:
                if sheet_name:
                    workbook_values[sheet_name] = cell_values
                workbook_values.setdefault(name, cell_values)

        if shared_strings is not None and shared_strings_key in xml_files:
            xml_files[shared_strings_key] = self._serialise_shared_strings(shared_strings)

        return xml_files, workbook_values

    def _sync_excel_tables(
        self,
        xml_files: dict[str, str],
        files: dict[str, bytes],
        sheet_map: dict[str, str],
        workbook_values: dict[str, dict[str, str]],
    ) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
        if not sheet_map:
            return xml_files, {}

        tables: dict[str, dict[str, object]] = {}
        lower_lookup: dict[str, str] = {}

        for sheet_path, sheet_name in sheet_map.items():
            sheet_xml = xml_files.get(sheet_path)
            if sheet_xml is None and sheet_path in files:
                sheet_xml = files[sheet_path].decode("utf-8")
            if not sheet_xml:
                continue

            table_data = self._extract_sheet_tables(
                sheet_path,
                sheet_name,
                sheet_xml,
                xml_files,
                files,
                workbook_values,
            )
            if not table_data:
                continue

            for table_name, info in table_data.items():
                tables[table_name] = info
                lower_lookup[table_name.lower()] = table_name

        if tables:
            tables["__lower__"] = lower_lookup

        return xml_files, tables

    def _extract_sheet_tables(
        self,
        sheet_path: str,
        sheet_name: str,
        sheet_xml: str,
        xml_files: dict[str, str],
        files: dict[str, bytes],
        workbook_values: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, object]]:
        try:
            sheet_tree = etree.fromstring(sheet_xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return {}

        ns = sheet_tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""
        r_ns = sheet_tree.nsmap.get("r")
        default_r_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        r_prefix = f"{{{r_ns}}}" if r_ns else f"{{{default_r_ns}}}"

        rels_path = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
        rels_xml = xml_files.get(rels_path)
        if rels_xml is None and rels_path in files:
            rels_xml = files[rels_path].decode("utf-8")
        rel_targets = self._parse_relationship_targets(rels_xml)

        row_columns = self._map_sheet_columns(sheet_tree)

        tables: dict[str, dict[str, object]] = {}
        for table_part in sheet_tree.findall(f".//{prefix}tablePart"):
            rel_id = table_part.get(f"{r_prefix}id")
            if not rel_id:
                continue
            target = rel_targets.get(rel_id)
            if not target:
                continue
            table_path = self._normalise_excel_path(target, sheet_path)
            table_xml = xml_files.get(table_path)
            if table_xml is None and table_path in files:
                table_xml = files[table_path].decode("utf-8")
            if not table_xml:
                continue

            updated_xml, table_info = self._update_table_definition(
                table_xml,
                sheet_name,
                row_columns,
                workbook_values,
                sheet_path,
            )
            if updated_xml is not None:
                xml_files[table_path] = updated_xml
            if table_info is not None:
                tables[table_info["name"]] = table_info

        return tables

    def _normalise_excel_path(self, target: str, base_path: str) -> str:
        cleaned = target.strip()
        if not cleaned:
            return base_path
        if cleaned.startswith("/"):
            cleaned = cleaned[1:]
            return cleaned if cleaned.startswith("xl/") else f"xl/{cleaned}"

        base_dir = posixpath.dirname(base_path)
        combined = posixpath.normpath(posixpath.join(base_dir, cleaned))
        if not combined.startswith("xl/"):
            combined = posixpath.normpath(posixpath.join("xl", cleaned))
        if not combined.startswith("xl/"):
            combined = f"xl/{combined.lstrip('/')}"
        return combined

    def _parse_relationship_targets(self, xml: str | None) -> dict[str, str]:
        if not xml:
            return {}
        try:
            tree = etree.fromstring(xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return {}

        ns = tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""
        targets: dict[str, str] = {}
        for rel in tree.findall(f"{prefix}Relationship"):
            rel_id = rel.get("Id")
            target = rel.get("Target")
            if not rel_id or not target:
                continue
            targets[rel_id] = target
        return targets

    def _normalise_sheet_rows(self, xml: str) -> str:
        try:
            tree = etree.fromstring(xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return xml

        ns = tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""

        sheet_data = tree.find(f"{prefix}sheetData")
        if sheet_data is None:
            return xml

        rows = list(sheet_data.findall(f"{prefix}row"))
        if not rows:
            return xml

        filtered_rows: list[etree._Element] = []
        for row in rows:
            cells = row.findall(f"{prefix}c")
            if not cells:
                sheet_data.remove(row)
                continue
            if not any(self._cell_has_value(cell, prefix) for cell in cells):
                sheet_data.remove(row)
                continue
            filtered_rows.append(row)

        if not filtered_rows:
            return etree.tostring(tree, encoding="unicode")

        rows = filtered_rows

        # Determine the smallest referenced row index so we can normalise
        # templated worksheets that introduced leading control rows (for
        # example ``{%tr%}`` markers placed before the first data row).  Word
        # expects contiguous row numbers starting at 1 for the chart ranges to
        # remain valid. When Ghostwriter removes the control rows, the
        # remaining worksheet content can start at ``r="2"`` which leaves the
        # original chart formulas pointing at empty cells.  By tracking the
        # minimum row value used anywhere in the sheet we can shift everything
        # back into place after rendering.
        min_defined_row: int | None = None
        for row in rows:
            attr = row.get("r")
            if attr:
                try:
                    row_index = int(attr)
                except ValueError:
                    row_index = None
                if row_index is not None and (
                    min_defined_row is None or row_index < min_defined_row
                ):
                    min_defined_row = row_index
            for cell in row.findall(f"{prefix}c"):
                ref = cell.get("r")
                if not ref:
                    continue
                parsed = self._split_cell(ref)
                if parsed is None:
                    continue
                _col, row_index = parsed
                if min_defined_row is None or row_index < min_defined_row:
                    min_defined_row = row_index

        row_offset = max((min_defined_row or 1) - 1, 0)
        last_index = 0
        min_col: int | None = None
        max_col: int | None = None
        min_row: int | None = None
        max_row: int | None = None

        for row in rows:
            attr = row.get("r")
            try:
                candidate = int(attr) if attr else None
            except ValueError:
                candidate = None

            if candidate is not None:
                candidate = max(1, candidate - row_offset)

            target_index = last_index + 1
            if candidate is None or candidate <= last_index:
                row_index = target_index
            else:
                row_index = min(candidate, target_index)

            cells = []
            parsed_rows: list[int] = []
            removed_cells = False
            for cell in row.findall(f"{prefix}c"):
                if not self._cell_has_value(cell, prefix):
                    row.remove(cell)
                    removed_cells = True
                    continue
                ref = cell.get("r")
                parsed = self._split_cell(ref) if ref else None
                if parsed is not None:
                    col_index, parsed_row = parsed
                    parsed_row = max(1, parsed_row - row_offset)
                    parsed = (col_index, parsed_row)
                cells.append((cell, parsed))
                if parsed is not None:
                    parsed_rows.append(parsed[1])

            if not cells:
                parent = row.getparent()
                if parent is not None:
                    parent.remove(row)
                continue

            unique_rows = {value for value in parsed_rows}
            if candidate is None and parsed_rows:
                candidate = min(parsed_rows)
                if row_index > candidate:
                    row_index = candidate

            row.set("r", str(row_index))

            cols: list[int] = []
            row_rows: list[int] = []
            next_col = 0
            for cell, parsed in cells:
                if parsed is None or removed_cells:
                    col_index = next_col + 1
                    cell_row = row_index
                    if parsed is not None:
                        _, original_row = parsed
                        if len(unique_rows) > 1:
                            cell_row = original_row
                            row_index = max(row_index, cell_row)
                else:
                    col_index, original_row = parsed
                    if len(unique_rows) <= 1:
                        cell_row = row_index
                    else:
                        cell_row = original_row
                    row_index = max(row_index, cell_row)
                next_col = col_index
                cell.set("r", f"{self._column_letters(col_index)}{cell_row}")
                cols.append(col_index)
                row_rows.append(cell_row)

                if min_col is None or col_index < min_col:
                    min_col = col_index
                if max_col is None or col_index > max_col:
                    max_col = col_index

            if cols:
                row.set("spans", f"{min(cols)}:{max(cols)}")
            else:
                row.attrib.pop("spans", None)

            if row_rows:
                row.set("r", str(min(row_rows)))
                min_row_val = min(row_rows)
                max_row_val = max(row_rows)
                if min_row is None or min_row_val < min_row:
                    min_row = min_row_val
                if max_row is None or max_row_val > max_row:
                    max_row = max_row_val
                last_index = max(last_index, max_row_val)
            else:
                if min_row is None or row_index < min_row:
                    min_row = row_index
                if max_row is None or row_index > max_row:
                    max_row = row_index
                last_index = max(last_index, row_index)

        dimension = tree.find(f"{prefix}dimension")
        if min_row is not None and min_col is not None and max_col is not None and max_row is not None:
            ref = (
                f"{self._column_letters(min_col)}{min_row}:"
                f"{self._column_letters(max_col)}{max_row}"
            )
        else:
            ref = "A1"

        if dimension is None:
            tag = f"{prefix}dimension" if prefix else "dimension"
            dimension = etree.Element(tag)
            tree.insert(0, dimension)

        dimension.set("ref", ref)

        return etree.tostring(tree, encoding="unicode")

    def _cell_has_value(self, cell: etree._Element, prefix: str) -> bool:
        if cell.find(f"{prefix}f") is not None:
            return True

        value = cell.find(f"{prefix}v")
        if value is not None and value.text is not None and value.text.strip():
            return True

        inline = cell.find(f"{prefix}is")
        if inline is not None:
            text = "".join(
                node.text or ""
                for node in inline.findall(f".//{prefix}t")
            )
            if text.strip():
                return True

        return False

    def _map_sheet_columns(self, sheet_tree: etree._Element) -> dict[int, set[int]]:
        ns = sheet_tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""

        rows: dict[int, set[int]] = {}
        for row in sheet_tree.findall(f".//{prefix}row"):
            row_index = row.get("r")
            if row_index:
                try:
                    idx = int(row_index)
                except ValueError:
                    continue
            else:
                # Fallback: count rows sequentially if "r" missing
                idx = len(rows) + 1
            cols: set[int] = set()
            for cell in row.findall(f"{prefix}c"):
                cell_ref = cell.get("r")
                if not cell_ref:
                    continue
                parsed = self._split_cell(cell_ref)
                if parsed is None:
                    continue
                col_index, _ = parsed
                cols.add(col_index)
            rows[idx] = cols
        return rows

    def _update_table_definition(
        self,
        table_xml: str,
        sheet_name: str,
        row_columns: dict[int, set[int]],
        workbook_values: dict[str, dict[str, str]],
        sheet_path: str,
    ) -> tuple[str | None, dict[str, object] | None]:
        try:
            table_tree = etree.fromstring(table_xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return None, None

        ns = table_tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""

        table_name = table_tree.get("name") or table_tree.get("displayName")
        if not table_name:
            return None, None

        ref = table_tree.get("ref")
        if not ref:
            return None, None

        start_cell, end_cell = ref.split(":") if ":" in ref else (ref, ref)
        start = self._split_cell(start_cell)
        end = self._split_cell(end_cell)
        if start is None or end is None:
            return None, None

        start_col, start_row = start
        end_col, end_row = end

        header_rows = int(table_tree.get("headerRowCount", "1") or 0)
        totals_rows = int(table_tree.get("totalsRowCount", "0") or 0)
        data_start_row = start_row + header_rows
        data_end_row = end_row - totals_rows if totals_rows else end_row

        # Determine actual last data row based on rendered worksheet
        actual_end_row = data_start_row - 1
        for row_index in sorted(row_columns):
            if row_index < data_start_row:
                continue
            if totals_rows and row_index > data_end_row:
                continue
            columns = row_columns[row_index]
            if any(start_col <= col <= end_col for col in columns):
                actual_end_row = max(actual_end_row, row_index)

        if totals_rows:
            new_end_row = max(actual_end_row, data_start_row - 1) + totals_rows
        else:
            new_end_row = max(actual_end_row, data_start_row - 1)

        if new_end_row < data_start_row and not totals_rows:
            new_end_row = data_start_row - 1

        if new_end_row != end_row:
            end_row = new_end_row

        columns_in_use: set[int] = set()
        for row_index in range(start_row, end_row + 1):
            columns = row_columns.get(row_index)
            if not columns:
                continue
            for column_index in columns:
                if column_index >= start_col:
                    columns_in_use.add(column_index)

        sheet_values = (
            workbook_values.get(sheet_name)
            or workbook_values.get(sheet_path)
            or {}
        )

        header_values: dict[int, str] = {}
        if header_rows:
            for offset in range(header_rows):
                header_row = start_row + offset
                row_cols = row_columns.get(header_row, set())
                for column_index in row_cols:
                    if column_index < start_col:
                        continue
                    cell_ref = f"{self._column_letters(column_index)}{header_row}"
                    value = sheet_values.get(cell_ref)
                    if value is None:
                        continue
                    stripped = value.strip()
                    if not stripped:
                        continue
                    header_values.setdefault(column_index, stripped)

        if columns_in_use:
            actual_end_col = max(columns_in_use)
        else:
            actual_end_col = end_col

        if actual_end_col < start_col:
            actual_end_col = start_col

        if actual_end_col != end_col:
            end_col = actual_end_col

        new_ref = (
            f"{self._column_letters(start_col)}{start_row}:"
            f"{self._column_letters(end_col)}{end_row}"
        )
        table_tree.set("ref", new_ref)
        for auto_filter in table_tree.findall(f"{prefix}autoFilter"):
            auto_filter.set("ref", new_ref)

        table_columns = table_tree.find(f"{prefix}tableColumns")
        if table_columns is None:
            tag = f"{prefix}tableColumns" if prefix else "tableColumns"
            table_columns = etree.SubElement(table_tree, tag)

        existing_columns = list(table_columns.findall(f"{prefix}tableColumn"))
        desired_count = end_col - start_col + 1
        max_id = 0
        for column in existing_columns:
            try:
                max_id = max(max_id, int(column.get("id", "0")))
            except ValueError:
                continue

        while len(existing_columns) > desired_count:
            column = existing_columns.pop()
            table_columns.remove(column)

        while len(existing_columns) < desired_count:
            max_id += 1
            column = etree.SubElement(table_columns, f"{prefix}tableColumn")
            column.set("id", str(max_id))
            column.set("name", f"Column{max_id}")
            existing_columns.append(column)

        column_names: list[str] = []
        for offset, column in enumerate(existing_columns):
            column_index = start_col + offset
            header_value = header_values.get(column_index)
            if header_value is None or not header_value.strip():
                header_value = column.get("name") or column.get("id") or f"Column{offset + 1}"
            column.set("name", header_value)
            column_names.append(header_value)

        table_columns.set("count", str(len(existing_columns)))

        if not column_names:
            width = end_col - start_col + 1
            column_names = [f"Column{idx}" for idx in range(1, width + 1)]

        table_info: dict[str, object] = {
            "name": table_name,
            "sheet": sheet_name,
            "columns": {},
            "order": column_names,
        }

        data_end_row = end_row - totals_rows if totals_rows else end_row

        columns_info: dict[str, dict[str, list[str]]] = {}
        for offset, column_name in enumerate(column_names):
            column_index = start_col + offset
            column_letter = self._column_letters(column_index)

            headers = [
                f"{column_letter}{row_index}"
                for row_index in range(start_row, start_row + header_rows)
            ] if header_rows else []

            data_cells = [
                f"{column_letter}{row_index}"
                for row_index in range(data_start_row, data_end_row + 1)
            ] if data_start_row <= data_end_row else []

            totals_cells = [
                f"{column_letter}{row_index}"
                for row_index in range(data_end_row + 1, end_row + 1)
            ] if totals_rows else []

            columns_info[column_name] = {
                "headers": headers,
                "data": data_cells,
                "totals": totals_cells,
            }

        table_info["columns"] = columns_info

        return etree.tostring(table_tree, encoding="unicode"), table_info

    def _parse_shared_strings(self, xml: str) -> tuple[list[str], etree._Element]:
        try:
            tree = etree.fromstring(xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return [], etree.Element("sharedStrings")

        ns = tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""
        values: list[str] = []
        for si in tree.findall(f"{prefix}si"):
            text = "".join(t.text or "" for t in si.findall(f".//{prefix}t"))
            values.append(text)
        return values, tree

    def _serialise_shared_strings(self, parsed: tuple[list[str], etree._Element]) -> str:
        values, tree = parsed
        ns = tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""
        for idx, si in enumerate(tree.findall(f"{prefix}si")):
            text = values[idx] if idx < len(values) else ""
            t_elements = si.findall(f".//{prefix}t")
            if not t_elements:
                etree.SubElement(si, f"{prefix}t").text = text
                continue

            t_elements[0].text = text
            for extra in t_elements[1:]:
                parent = extra.getparent()
                if parent is not None:
                    parent.remove(extra)
        return etree.tostring(tree, encoding="unicode")

    def _coerce_sheet_types(
        self,
        xml: str,
        shared_strings: tuple[list[str], etree._Element] | None,
    ) -> tuple[str, dict[str, str]]:
        try:
            tree = etree.fromstring(xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return xml, {}

        ns = tree.nsmap.get(None)
        prefix = f"{{{ns}}}" if ns else ""

        shared_values = shared_strings[0] if shared_strings else []
        cell_values: dict[str, str] = {}
        for cell in tree.findall(f".//{prefix}c"):
            cell_type = cell.get("t")
            cell_ref = cell.get("r")
            value_text: str | None = None
            if cell_type == "s":
                value_node = cell.find(f"{prefix}v")
                if value_node is None or value_node.text is None:
                    if cell_ref and cell_ref not in cell_values:
                        cell_values[cell_ref] = ""
                    continue
                try:
                    index = int(value_node.text)
                except (TypeError, ValueError):
                    if cell_ref and cell_ref not in cell_values:
                        cell_values[cell_ref] = value_node.text or ""
                    continue
                if 0 <= index < len(shared_values):
                    original_value = shared_values[index]
                    coerced = self._maybe_numeric(original_value)
                    if coerced is not None:
                        cell.attrib.pop("t", None)
                        value_node.text = coerced
                        shared_values[index] = coerced
                        value_text = coerced
                    else:
                        value_text = original_value
                if cell_ref and value_text is not None:
                    cell_values[cell_ref] = value_text
                elif cell_ref and cell_ref not in cell_values:
                    cell_values[cell_ref] = ""
                continue

            if cell_type in _INLINE_STRING_TYPES:
                inline = cell.find(f"{prefix}is")
                if inline is None:
                    if cell_ref and cell_ref not in cell_values:
                        cell_values[cell_ref] = ""
                    continue
                text_nodes = inline.findall(f".//{prefix}t")
                text = "".join(node.text or "" for node in text_nodes)
                coerced = self._maybe_numeric(text)
                if coerced is None:
                    value_text = text
                    if cell_ref:
                        cell_values[cell_ref] = value_text
                    continue
                cell.attrib.pop("t", None)
                for node in text_nodes:
                    parent = node.getparent()
                    if parent is not None:
                        parent.remove(node)
                inline_parent = inline.getparent()
                if inline_parent is not None:
                    inline_parent.remove(inline)
                value_node = etree.SubElement(cell, f"{prefix}v")
                value_node.text = coerced
                value_text = coerced
                if cell_ref:
                    cell_values[cell_ref] = value_text
                continue

            if cell_type == "str" or cell_type == "b":
                value_node = cell.find(f"{prefix}v")
                if value_node is None or value_node.text is None:
                    if cell_ref and cell_ref not in cell_values:
                        cell_values[cell_ref] = ""
                    continue
                coerced = self._maybe_numeric(value_node.text)
                if coerced is not None:
                    cell.attrib.pop("t", None)
                    value_node.text = coerced
                    value_text = coerced
                else:
                    value_text = value_node.text
                if cell_ref:
                    cell_values[cell_ref] = value_text
                continue

            value_node = cell.find(f"{prefix}v")
            if value_node is not None and value_node.text is not None:
                value_text = value_node.text
            if cell_ref and value_text is not None:
                cell_values[cell_ref] = value_text

        return etree.tostring(tree, encoding="unicode"), cell_values

    def _maybe_numeric(self, value: str) -> str | None:
        stripped = value.strip()
        if not stripped:
            return None
        if re.fullmatch(r"-?\d+", stripped):
            return str(int(stripped))
        if re.fullmatch(r"-?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?", stripped):
            number = float(stripped)
            if number.is_integer():
                return str(int(number))
            return (
                ("%f" % number).rstrip("0").rstrip(".")
                if "e" not in stripped.lower()
                else stripped
            )
        return None

    # Chart helpers -------------------------------------------------

    def _sync_chart_cache(
        self,
        xml: str,
        part,
        excel_values: dict[str, dict[str, dict[str, str]]],
    ) -> str:
        try:
            tree = etree.fromstring(xml.encode("utf-8"))
        except etree.XMLSyntaxError:
            return xml

        updated = False

        workbook_data = self._resolve_chart_workbook(part, excel_values)

        if workbook_data:
            for num_ref in tree.findall(".//{*}numRef"):
                formula = self._find_chart_formula(num_ref)
                if not formula:
                    continue
                values = self._extract_range_values(formula, workbook_data)
                if values is None:
                    continue
                cache = self._find_or_create_cache(num_ref, "numCache")
                self._write_cache(cache, values)
                self._write_literal_cache(num_ref, "numLit", values)
                updated = True

            for str_ref in tree.findall(".//{*}strRef"):
                formula = self._find_chart_formula(str_ref)
                if not formula:
                    continue
                values = self._extract_range_values(formula, workbook_data)
                if values is None:
                    continue
                cache = self._find_or_create_cache(str_ref, "strCache")
                self._write_cache(cache, values)
                self._write_literal_cache(str_ref, "strLit", values)
                updated = True

        repaired = self._repair_chart_caches(tree)

        if not updated and not repaired:
            return xml

        return etree.tostring(tree, encoding="unicode")

    def _resolve_chart_workbook(
        self,
        part,
        excel_values: dict[str, dict[str, dict[str, str]]],
    ) -> dict[str, dict[str, str]] | None:
        rels = getattr(part, "rels", None)
        if not rels:
            return None

        for rel in rels.values():
            reltype = getattr(rel, "reltype", "")
            if not reltype or "embeddedPackage" not in reltype:
                continue
            target = getattr(rel, "target_part", None)
            if target is None:
                continue
            partname = self._normalise_partname(target)
            workbook_data = excel_values.get(partname)
            if workbook_data:
                return workbook_data
        return None

    def _find_chart_formula(self, ref_node) -> str | None:
        for child in ref_node:
            qname = etree.QName(child)
            if qname.localname != "f":
                continue
            if child.text is None:
                return None
            return child.text.strip()
        return None

    def _find_or_create_cache(self, ref_node, local_name: str):
        for child in ref_node:
            if etree.QName(child).localname == local_name:
                return child

        namespace = etree.QName(ref_node).namespace
        tag = f"{{{namespace}}}{local_name}" if namespace else local_name
        return etree.SubElement(ref_node, tag)

    def _write_literal_cache(self, ref_node, local_name: str, values: list[str]) -> None:
        parent = ref_node.getparent()
        if parent is None:
            return

        literal = None
        for child in parent:
            if etree.QName(child).localname == local_name:
                literal = child
                break

        if literal is None:
            namespace = etree.QName(ref_node).namespace
            tag = f"{{{namespace}}}{local_name}" if namespace else local_name
            literal = etree.SubElement(parent, tag)

        self._write_cache(literal, values)

    def _extract_range_values(
        self,
        formula: str,
        workbook_data: dict[str, dict[str, str]],
    ) -> list[str] | None:
        if not formula:
            return None

        if "(" in formula and ")" in formula:
            inner = formula[formula.find("(") + 1 : formula.rfind(")")]
            parts = self._split_formula_arguments(inner)
            values: list[str] = []
            for part in parts:
                extracted = self._extract_range_values(part, workbook_data)
                if extracted:
                    values.extend(extracted)
            return values or None

        sheet_name = None
        cell_part = formula
        if "!" in formula:
            sheet_part, cell_part = formula.rsplit("!", 1)
            sheet_name = self._normalise_sheet_name(sheet_part)

        if "[" in cell_part and "]" in cell_part:
            structured = self._extract_structured_reference(
                sheet_name,
                cell_part,
                workbook_data,
            )
            if structured is not None:
                return structured

        if sheet_name is None:
            return None

        sheet_values = workbook_data.get(sheet_name)
        if sheet_values is None:
            return None

        cells = self._expand_cell_range(cell_part)
        if not cells:
            return None

        values = [sheet_values.get(cell, "") for cell in cells]
        return values

    def _split_formula_arguments(self, formula: str) -> list[str]:
        depth = 0
        current: list[str] = []
        parts: list[str] = []
        for char in formula:
            if char == "," and depth == 0:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
                continue
            if char == "(":
                depth += 1
            elif char == ")" and depth > 0:
                depth -= 1
            current.append(char)
        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return parts

    def _normalise_sheet_name(self, sheet_part: str) -> str | None:
        stripped = sheet_part.strip()
        if stripped.startswith("="):
            stripped = stripped[1:]
        if stripped.startswith("'") and stripped.endswith("'"):
            stripped = stripped[1:-1]
        if stripped.startswith("[") and "]" in stripped:
            stripped = stripped.split("]", 1)[1]
        if stripped.startswith("'") and stripped.endswith("'"):
            stripped = stripped[1:-1]
        return stripped or None

    def _expand_cell_range(self, cell_part: str) -> list[str]:
        reference = cell_part.strip()
        if reference.startswith("="):
            reference = reference[1:]
        if not reference:
            return []

        ranges = [r.strip() for r in reference.split(",") if r.strip()]
        cells: list[str] = []
        for cell_range in ranges:
            start_end = cell_range.split(":")
            if len(start_end) == 1:
                coord = self._normalise_cell_reference(start_end[0])
                if coord:
                    cells.append(coord)
                continue
            if len(start_end) != 2:
                continue
            start = self._split_cell(start_end[0])
            end = self._split_cell(start_end[1])
            if start is None or end is None:
                continue
            start_col, start_row = start
            end_col, end_row = end
            for col in range(start_col, end_col + 1):
                for row in range(start_row, end_row + 1):
                    cells.append(f"{self._column_letters(col)}{row}")
        return cells

    def _extract_structured_reference(
        self,
        sheet_name: str | None,
        reference: str,
        workbook_data: dict[str, dict[str, str]],
    ) -> list[str] | None:
        tables = workbook_data.get("__tables__")
        if not isinstance(tables, dict):
            return None

        table_name, tokens = self._parse_structured_reference(reference)
        if not table_name:
            return None

        table_info = tables.get(table_name)
        if table_info is None:
            lower_lookup = tables.get("__lower__")
            if isinstance(lower_lookup, dict):
                resolved = lower_lookup.get(table_name.lower())
                if resolved:
                    table_info = tables.get(resolved)
        if not isinstance(table_info, dict):
            return None

        resolved_sheet = sheet_name or table_info.get("sheet")
        if not isinstance(resolved_sheet, str) or not resolved_sheet:
            return None

        sheet_values = workbook_data.get(resolved_sheet)
        if sheet_values is None:
            return None

        qualifiers, columns = self._interpret_structured_tokens(tokens, table_info)
        if columns is None or not columns:
            return None

        values: list[str] = []
        columns_info = table_info.get("columns")
        if not isinstance(columns_info, dict):
            return None

        include_headers = qualifiers.get("headers", False)
        include_data = qualifiers.get("data", False)
        include_totals = qualifiers.get("totals", False)

        for column_name in columns:
            column_info = columns_info.get(column_name)
            if not isinstance(column_info, dict):
                continue
            if include_headers:
                for cell in column_info.get("headers", []):
                    values.append(sheet_values.get(cell, ""))
            if include_data:
                for cell in column_info.get("data", []):
                    values.append(sheet_values.get(cell, ""))
            if include_totals:
                for cell in column_info.get("totals", []):
                    values.append(sheet_values.get(cell, ""))

        return values or None

    def _parse_structured_reference(
        self,
        reference: str,
    ) -> tuple[str | None, list[object]]:
        cleaned = reference.strip()
        if cleaned.startswith("="):
            cleaned = cleaned[1:]
        if not cleaned:
            return None, []

        if "[" not in cleaned:
            return self._strip_structured_quotes(cleaned), []

        name_part, rest = cleaned.split("[", 1)
        table_name = self._strip_structured_quotes(name_part)
        tokens = self._split_structured_tokens("[" + rest)
        return table_name, tokens

    def _split_structured_tokens(self, token_str: str) -> list[object]:
        tokens: list[str] = []
        current: list[str] = []
        depth = 0
        for char in token_str:
            if char == "[":
                depth += 1
                if depth == 1:
                    current = []
                    continue
            elif char == "]":
                depth -= 1
                if depth == 0:
                    token = "".join(current).strip()
                    if token:
                        tokens.append(token)
                    current = []
                    continue
            elif char == "," and depth == 1:
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current = []
                continue

            if depth >= 1:
                current.append(char)

        normalised: list[object] = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            if ":" in token:
                start, end = token.split(":", 1)
                start = self._strip_structured_component(start)
                end = self._strip_structured_component(end)
                if start and end:
                    normalised.append((start, end))
                continue
            normalised.append(self._strip_structured_component(token))
        return normalised

    def _strip_structured_component(self, component: str) -> str:
        result = component.strip()
        while result.startswith("[") and result.endswith("]") and len(result) >= 2:
            result = result[1:-1].strip()
        return self._strip_structured_quotes(result)

    def _strip_structured_quotes(self, value: str) -> str | None:
        stripped = value.strip()
        if stripped.startswith("'") and stripped.endswith("'") and len(stripped) >= 2:
            stripped = stripped[1:-1]
        return stripped or None

    def _interpret_structured_tokens(
        self,
        tokens: list[object],
        table_info: dict[str, object],
    ) -> tuple[dict[str, bool], list[str] | None]:
        order = table_info.get("order")
        if not isinstance(order, list):
            order = []
        order_lookup = {name: idx for idx, name in enumerate(order) if isinstance(name, str)}

        qualifier_flags: set[str] = set()
        selected_indices: list[int] = []

        def add_column(name: str | None) -> None:
            if not name:
                return
            idx = order_lookup.get(name)
            if idx is None:
                return
            if idx not in selected_indices:
                selected_indices.append(idx)

        for token in tokens:
            if isinstance(token, tuple):
                start, end = token
                if not isinstance(start, str) or not isinstance(end, str):
                    continue
                start_idx = order_lookup.get(start)
                end_idx = order_lookup.get(end)
                if start_idx is None or end_idx is None:
                    continue
                if start_idx <= end_idx:
                    indices = range(start_idx, end_idx + 1)
                else:
                    indices = range(end_idx, start_idx + 1)
                for idx in indices:
                    if idx not in selected_indices:
                        selected_indices.append(idx)
                continue

            if isinstance(token, str):
                lowered = token.lower()
                if lowered.startswith("#"):
                    qualifier_flags.add(lowered)
                    continue
                add_column(token)

        if not selected_indices:
            selected_indices = list(range(len(order)))

        qualifiers = {
            "headers": "#headers" in qualifier_flags or "#all" in qualifier_flags,
            "data": bool(
                {"#data", "#all"}.intersection(qualifier_flags)
                or not qualifier_flags
            ),
            "totals": "#totals" in qualifier_flags or "#all" in qualifier_flags,
        }

        if "#this row" in qualifier_flags:
            return qualifiers, None

        columns = [order[idx] for idx in sorted(selected_indices) if idx < len(order)]
        return qualifiers, columns

    def _normalise_cell_reference(self, cell: str) -> str | None:
        parsed = self._split_cell(cell)
        if parsed is None:
            return None
        col, row = parsed
        return f"{self._column_letters(col)}{row}"

    def _split_cell(self, cell: str) -> tuple[int, int] | None:
        cleaned = cell.strip().replace("$", "")
        match = re.fullmatch(r"([A-Za-z]+)(\d+)", cleaned)
        if not match:
            return None
        col_letters, row_str = match.groups()
        col_index = 0
        for char in col_letters.upper():
            col_index = col_index * 26 + (ord(char) - ord("A") + 1)
        return col_index, int(row_str)

    def _column_letters(self, index: int) -> str:
        letters: list[str] = []
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            letters.append(chr(ord("A") + remainder))
        return "".join(reversed(letters))

    def _write_cache(self, cache, values: list[str]) -> None:
        namespace = etree.QName(cache).namespace
        prefix = f"{{{namespace}}}" if namespace else ""
        pt_count = cache.find(f"{prefix}ptCount")
        if pt_count is None:
            pt_count = etree.SubElement(cache, f"{prefix}ptCount")
        pt_count.set("val", str(len(values)))

        for pt in list(cache.findall(f"{prefix}pt")):
            cache.remove(pt)

        for idx, value in enumerate(values):
            pt = etree.SubElement(cache, f"{prefix}pt", idx=str(idx))
            v = etree.SubElement(pt, f"{prefix}v")
            v.text = "" if value is None else str(value)

    def _repair_chart_caches(self, tree: etree._Element) -> bool:
        """Ensure declared chart cache counts match the cached point entries."""

        repaired = False
        for cache in tree.findall(".//{*}numCache") + tree.findall(".//{*}numLit"):
            if self._repair_single_chart_cache(cache, fill_value="0"):
                repaired = True

        for cache in tree.findall(".//{*}strCache") + tree.findall(".//{*}strLit"):
            if self._repair_single_chart_cache(cache, fill_value=""):
                repaired = True

        return repaired

    def _repair_single_chart_cache(self, cache, fill_value: str) -> bool:
        namespace = etree.QName(cache).namespace
        prefix = f"{{{namespace}}}" if namespace else ""

        changed = False

        pts = list(cache.findall(f"{prefix}pt"))
        for idx, pt in enumerate(pts):
            if pt.get("idx") != str(idx):
                pt.set("idx", str(idx))
                changed = True
            value_node = pt.find(f"{prefix}v")
            if value_node is None:
                value_node = etree.SubElement(pt, f"{prefix}v")
                changed = True
            if value_node.text is None:
                value_node.text = fill_value
                changed = True

        pt_count = cache.find(f"{prefix}ptCount")
        declared = None
        if pt_count is not None:
            val_attr = pt_count.get("val")
            try:
                declared = int(val_attr) if val_attr is not None else None
            except (TypeError, ValueError):
                declared = None

        actual = len(pts)

        if pt_count is None:
            pt_count = etree.SubElement(cache, f"{prefix}ptCount")
            changed = True

        if declared is None:
            declared = actual
        if declared < actual:
            declared = actual
        elif declared > actual:
            for idx in range(actual, declared):
                pt = etree.SubElement(cache, f"{prefix}pt", idx=str(idx))
                value_node = etree.SubElement(pt, f"{prefix}v")
                value_node.text = fill_value
            actual = declared
            changed = True

        if pt_count.get("val") != str(actual):
            pt_count.set("val", str(actual))
            changed = True

        return changed

