# Standard Libraries
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

# Django Imports
from django.contrib.messages import get_messages
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils.dateformat import format as dateformat
from django.utils.encoding import force_str

# 3rd Party Libraries
from rest_framework.renderers import JSONRenderer

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import (
    ExtraFieldModel,
    ExtraFieldSpec,
    ReportConfiguration,
)
from ghostwriter.factories import (
    ClientFactory,
    DocTypeFactory,
    EvidenceFactory,
    ExtraFieldModelFactory,
    ExtraFieldSpecFactory,
    FindingFactory,
    FindingNoteFactory,
    FindingTypeFactory,
    GenerateMockProject,
    LocalFindingNoteFactory,
    ObservationFactory,
    OplogEntryEvidenceFactory,
    OplogEntryFactory,
    OplogEntryRecordingFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectTargetFactory,
    ReportDocxTemplateFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportObservationLinkFactory,
    ReportPptxTemplateFactory,
    ReportTemplateFactory,
    SeverityFactory,
    UserFactory,
)
from ghostwriter.modules.custom_serializers import ReportDataSerializer
from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter.jinja_funcs import (
    add_days,
    compromised,
    filter_bhe_findings_by_domain,
    filter_severity,
    filter_tags,
    filter_type,
    format_datetime,
    to_datetime,
    business_days,
    get_item,
    regex_search,
    replace_blanks,
    strip_html,
    translate_domain_sid,
)
from ghostwriter.reporting.models import (
    Evidence,
    EvidenceImageAlignmentOverride,
    ReportFindingLink,
    ReportObservationLink,
)
from ghostwriter.reporting.templatetags import report_tags

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class IndexViewTests(TestCase):
    """Collection of tests for :view:`reporting.index`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:index")
        cls.redirect_uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertRedirects(response, self.redirect_uri)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.report = ReportFactory()
        for x in range(3):
            ReportFindingLinkFactory(report=cls.report)

    def setUp(self):
        pass

    def test_tags(self):
        queryset = self.ReportFindingLink.objects.all()

        severity_dict = report_tags.group_by_severity(queryset)
        self.assertEqual(len(severity_dict), 3)

        for group in severity_dict:
            self.assertEqual(
                report_tags.get_item(severity_dict, group), severity_dict.get(group)
            )

    def test_file_filers(self):
        img_evidence = EvidenceFactory(img=True)
        txt_evidence = EvidenceFactory(txt=True)
        unknown_evidence = EvidenceFactory(unknown=True)
        deleted_evidence = EvidenceFactory()
        os.remove(deleted_evidence.document.path)

        self.assertTrue(report_tags.get_file_type(img_evidence) == "image")
        self.assertTrue(report_tags.get_file_type(txt_evidence) == "text")
        self.assertTrue(report_tags.get_file_type(unknown_evidence) == "unknown")
        self.assertTrue(report_tags.get_file_type(deleted_evidence) == "missing")

        self.assertEqual(report_tags.get_file_content(txt_evidence), "lorem ipsum")
        self.assertEqual(
            report_tags.get_file_content(deleted_evidence), "FILE NOT FOUND"
        )

    def test_file_content_xss_escaping(self):
        """Verify that HTML/JS in an evidence text file is escaped when rendered in the template."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.template.loader import render_to_string
        from django.utils.safestring import SafeData

        from ghostwriter.commandcenter.models import ReportConfiguration

        xss_payload = b"<script>alert('xss')</script>"
        xss_evidence = EvidenceFactory(
            document=SimpleUploadedFile(
                "evidence.txt", xss_payload, content_type="text/plain"
            )
        )

        # The template tag must never return a SafeData instance (which would bypass auto-escaping)
        raw = report_tags.get_file_content(xss_evidence)
        self.assertNotIsInstance(
            raw, SafeData, "get_file_content must not return mark_safe/SafeData"
        )
        self.assertIn("<script>", raw)  # raw string is unescaped

        # When rendered through the template the tags must be escaped
        report_config = ReportConfiguration.get_solo()
        rendered = render_to_string(
            "snippets/evidence_display.html",
            {
                "evidence": xss_evidence,
                "report_config": report_config,
                "clickable": False,
            },
        )
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_field_spec_filters(self):
        report_extra_field = ExtraFieldModelFactory(
            model_internal_name="reporting.Report", model_display_name="Reports"
        )
        ExtraFieldSpecFactory(
            internal_name="test_rt_field",
            display_name="Test RT Field",
            type="rich_text",
            target_model=report_extra_field,
        )
        field_spec = ExtraFieldSpec.objects.filter(target_model="reporting.Report")
        self.assertFalse(report_tags.has_non_rt_fields(field_spec))
        ExtraFieldSpecFactory(
            internal_name="test_field",
            display_name="Test Field",
            type="single_line_text",
            target_model=report_extra_field,
        )
        field_spec = ExtraFieldSpec.objects.filter(target_model="reporting.Report")
        self.assertTrue(report_tags.has_non_rt_fields(field_spec))

    def test_rich_text_extra_field_renders_report_evidence_previews(self):
        report_config = ReportConfiguration.get_solo()
        report_config.enable_borders = True
        report_config.border_weight = 19050
        report_config.border_color = "FF0000"
        report_config.evidence_image_width = 7.0
        report_config.evidence_image_alignment = "RIGHT"
        report_config.figure_caption_location = "top"
        report_config.save()
        template = ReportDocxTemplateFactory(
            evidence_image_width=4.25,
            evidence_image_alignment=EvidenceImageAlignmentOverride.LEFT,
        )
        report = ReportFactory(docx_template=template)
        evidence = EvidenceFactory(
            img=True,
            report=report,
            friendly_name="Preview Image",
            caption="Preview image caption",
        )
        text_evidence = EvidenceFactory(
            txt=True, report=report, friendly_name="Preview Text"
        )
        extra_evidences = [
            EvidenceFactory(
                img=True, report=report, friendly_name=f"Preview Image {index}"
            )
            for index in range(10)
        ]
        field_spec = ExtraFieldSpecFactory(
            internal_name="narrative",
            display_name="Narrative",
            type="rich_text",
            target_model=ExtraFieldModelFactory(
                model_internal_name="reporting.Report",
                model_display_name="Reports",
            ),
        )
        report.extra_fields = {
            "narrative": (
                '<script>alert("xss")</script>'
                '<div class="richtext-evidence" data-evidence-id="{}"></div>'
                '<div class="richtext-evidence" data-evidence-id="{}"></div>'
                "{}"
                "<p>Rendered text</p>"
            ).format(
                evidence.pk,
                text_evidence.pk,
                "".join(
                    '<div class="richtext-evidence" data-evidence-id="{}"></div>'.format(
                        extra_evidence.pk
                    )
                    for extra_evidence in extra_evidences
                ),
            )
        }

        rendered = render_to_string(
            "user_extra_fields/extra_field_modal.html",
            {
                "extra_fields": report.extra_fields,
                "field_spec": field_spec,
                "preview_report": report,
            },
        )

        self.assertIn(
            "This preview closely approximates report output using the report configuration and selected Word template settings.",
            rendered,
        )
        self.assertIn(
            'src="/reporting/evidence/download/{}"'.format(evidence.pk), rendered
        )
        self.assertIn('alt="Preview Image"', rendered)
        self.assertIn("text-left", rendered)
        self.assertIn("text-align: left", rendered)
        self.assertIn("display: inline-block", rendered)
        self.assertIn("width: 4.25in", rendered)
        self.assertIn("border: 2.0px solid #FF0000", rendered)
        self.assertLess(
            rendered.index("Preview image caption"),
            rendered.index('src="/reporting/evidence/download/{}"'.format(evidence.pk)),
        )
        self.assertIn(
            '<pre class="evidence-preview-clickable js-open-lightbox" style="cursor: pointer;"',
            rendered,
        )
        self.assertIn("<code>lorem ipsum</code>", rendered)
        self.assertNotIn('class="text-evidence', rendered)
        self.assertIn("Rendered text", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("GW_EVIDENCE_PREVIEW", rendered)
        self.assertNotIn("0<p>Rendered text</p>", rendered)

    def test_rich_text_extra_field_image_preview_uses_global_defaults(self):
        report_config = ReportConfiguration.get_solo()
        report_config.enable_borders = False
        report_config.evidence_image_width = 5.5
        report_config.evidence_image_alignment = "CENTER"
        report_config.figure_caption_location = "bottom"
        report_config.save()
        report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(
                evidence_image_width=None,
                evidence_image_alignment=EvidenceImageAlignmentOverride.USE_GLOBAL,
            )
        )
        evidence = EvidenceFactory(
            img=True, report=report, caption="Global default caption"
        )
        field_spec = ExtraFieldSpecFactory(
            internal_name="narrative",
            display_name="Narrative",
            type="rich_text",
            target_model=ExtraFieldModelFactory(
                model_internal_name="reporting.Report",
                model_display_name="Reports",
            ),
        )
        report.extra_fields = {
            "narrative": '<div class="richtext-evidence" data-evidence-id="{}"></div>'.format(
                evidence.pk
            )
        }

        rendered = render_to_string(
            "user_extra_fields/field.html",
            {
                "extra_fields": report.extra_fields,
                "field_spec": field_spec,
                "preview_report": report,
            },
        )

        self.assertIn("text-center", rendered)
        self.assertIn("text-align: center", rendered)
        self.assertIn("width: 5.5in", rendered)
        self.assertNotIn("border:", rendered)
        self.assertLess(
            rendered.index('src="/reporting/evidence/download/{}"'.format(evidence.pk)),
            rendered.index("Global default caption"),
        )

    def test_truncate_filename_filter(self):
        filename = "This is a long filename that should be truncated.txt"
        self.assertEqual(report_tags.truncate_filename(filename, 15), "This i...ed.txt")


# Tests verifying injection and XSS are not possible via evidence uploads and display


class EvidenceInjectionTests(TestCase):
    """
    Security tests verifying that XSS and HTML/JS injection attacks cannot be
    carried out via evidence file content, evidence metadata (friendly_name,
    caption), or the evidence download endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

    def setUp(self):
        self.client_mgr = Client()
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    # --- Extension allowlist ---

    def test_extension_allowlist_rejects_dangerous_types(self):
        """Extension validator must reject file types that could be served as active content."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile

        from ghostwriter.reporting.validators import validate_evidence_extension

        dangerous = ["html", "svg", "js", "php", "py", "rb", "sh", "xml", "htm"]
        for ext in dangerous:
            bad_file = SimpleUploadedFile(f"evil.{ext}", b"content")
            with self.assertRaises(
                DjangoValidationError, msg=f".{ext} should be rejected"
            ):
                validate_evidence_extension(bad_file)

    def test_extension_allowlist_accepts_safe_types(self):
        """Extension validator must accept the declared safe types without raising."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from ghostwriter.reporting.validators import validate_evidence_extension

        safe = ["txt", "log", "md", "png", "jpg", "jpeg"]
        for ext in safe:
            safe_file = SimpleUploadedFile(f"evidence.{ext}", b"content")
            validate_evidence_extension(safe_file)  # must not raise

    # --- Template rendering: HTML context ---

    def _render_evidence_display(
        self, friendly_name, caption, file_content=b"safe content"
    ):
        """Helper: render evidence_display.html with the given metadata."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.template.loader import render_to_string

        from ghostwriter.commandcenter.models import ReportConfiguration

        evidence = EvidenceFactory(
            friendly_name=friendly_name,
            caption=caption,
            document=SimpleUploadedFile("evidence.txt", file_content),
        )
        report_config = ReportConfiguration.get_solo()
        return render_to_string(
            "snippets/evidence_display.html",
            {"evidence": evidence, "report_config": report_config, "clickable": True},
        )

    def test_template_escapes_script_tag_in_friendly_name(self):
        """A <script> tag in friendly_name must be HTML-escaped in the rendered output."""
        rendered = self._render_evidence_display(
            friendly_name="<script>alert('xss')</script>",
            caption="normal caption",
        )
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_template_escapes_script_tag_in_caption(self):
        """A <script> tag in caption must be HTML-escaped in the rendered output."""
        rendered = self._render_evidence_display(
            friendly_name="normal name",
            caption="<script>alert('xss')</script>",
        )
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_template_escapes_img_onerror_in_friendly_name(self):
        """An <img onerror=...> payload in friendly_name must be escaped."""
        rendered = self._render_evidence_display(
            friendly_name='<img src=x onerror="alert(1)">',
            caption="normal caption",
        )
        self.assertNotIn("<img src=x", rendered)

    # --- Template rendering: HTML attribute injection ---

    def test_template_escapes_quote_injection_in_data_attribute(self):
        """
        A double-quote in friendly_name must be entity-encoded so it cannot
        close the data-evidence-name attribute and inject new attributes/handlers.
        """
        payload = '" onmouseover="alert(document.cookie)" x="'
        rendered = self._render_evidence_display(
            friendly_name=payload,
            caption="normal caption",
        )
        self.assertNotIn('" onmouseover="', rendered)
        self.assertIn("&quot;", rendered)

    def test_template_escapes_single_quote_injection_in_data_attribute(self):
        """A single-quote in friendly_name must be entity-encoded."""
        payload = "' onmouseover='alert(1)' x='"
        rendered = self._render_evidence_display(
            friendly_name=payload,
            caption="normal caption",
        )
        self.assertNotIn("' onmouseover='", rendered)

    # --- File content XSS ---

    def test_template_escapes_script_tag_in_file_content(self):
        """HTML in a text evidence file must be escaped when rendered via the template."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.template.loader import render_to_string
        from django.utils.safestring import SafeData

        from ghostwriter.commandcenter.models import ReportConfiguration
        from ghostwriter.reporting.templatetags.report_tags import get_file_content

        xss = b"<script>alert('xss')</script>"
        evidence = EvidenceFactory(
            document=SimpleUploadedFile("evidence.txt", xss),
        )
        # The template tag must never return marked-safe content
        raw = get_file_content(evidence)
        self.assertNotIsInstance(raw, SafeData)

        report_config = ReportConfiguration.get_solo()
        rendered = render_to_string(
            "snippets/evidence_display.html",
            {"evidence": evidence, "report_config": report_config, "clickable": False},
        )
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    # --- Download response headers ---

    def test_download_sets_nosniff_header(self):
        """Every evidence download must include X-Content-Type-Options: nosniff."""
        evidence = EvidenceFactory()
        uri = reverse("reporting:evidence_download", kwargs={"pk": evidence.pk})
        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

    def test_inline_view_sets_csp_header(self):
        """Inline evidence viewing (?view=1) must include a Content-Security-Policy header."""
        evidence = EvidenceFactory()
        uri = reverse("reporting:evidence_download", kwargs={"pk": evidence.pk})
        response = self.client_mgr.get(f"{uri}?view=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Content-Security-Policy", response)

    def test_inline_view_csp_blocks_scripts(self):
        """The inline-view CSP must use default-src 'none' and must not permit script execution."""
        evidence = EvidenceFactory()
        uri = reverse("reporting:evidence_download", kwargs={"pk": evidence.pk})
        response = self.client_mgr.get(f"{uri}?view=1")
        csp = response.get("Content-Security-Policy", "")
        self.assertIn("default-src 'none'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("script-src", csp)

    # --- JS context in form error template ---

    def test_form_error_template_uses_escapejs_filter(self):
        """
        The evidence form error template must use |escapejs on all error strings.
        FileExtensionValidator echoes the raw file extension into its error message,
        so without |escapejs a crafted extension (e.g. containing a newline or
        backslash) could break the surrounding JS string literal.
        """
        import re

        template_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "templates",
                "reporting",
                "evidence_form_template.html",
            )
        )
        with open(template_path, encoding="utf-8") as f:
            source = f.read()

        raw_occurrences = re.findall(r"\{\{\s*error\s*\}\}", source)
        self.assertEqual(
            raw_occurrences,
            [],
            "Found {{ error }} without |escapejs — use {{ error|escapejs }} to "
            "prevent JS string injection via validator error messages.",
        )


# Tests related to report modification actions


class AssignBlankFindingTests(TestCase):
    """Collection of tests for :view:`reporting.AssignBlankFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        # These must exist for the view to function
        cls.high_severity = SeverityFactory(severity="High", weight=1)
        cls.med_severity = SeverityFactory(severity="Medium", weight=2)
        cls.low_severity = SeverityFactory(severity="Low", weight=3)
        cls.info_severity = SeverityFactory(severity="Informational", weight=4)
        cls.finding_type = FindingTypeFactory(finding_type="Network")

        cls.uri = reverse(
            "reporting:assign_blank_finding", kwargs={"pk": cls.report.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.post(self.uri)
        self.assertTrue(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + self.uri)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

        ProjectAssignmentFactory(operator=self.user, project=self.report.project)
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_blank_finding_assigned_to_requesting_user(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        rfl = ReportFindingLink.objects.filter(report=self.report).last()
        self.assertIsNotNone(rfl)
        self.assertEqual(rfl.assigned_to, self.mgr_user)


class ConvertFindingTests(TestCase):
    """Collection of tests for :view:`reporting.ConvertFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = ReportFindingLinkFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("reporting:convert_finding", kwargs={"pk": cls.finding.pk})
        cls.redirect_uri = reverse(
            "reporting:finding_detail", kwargs={"pk": cls.finding.pk}
        )
        cls.failure_redirect_uri = f"{reverse('reporting:report_detail', kwargs={'pk': cls.finding.report.pk})}#findings"

        ProjectAssignmentFactory(operator=cls.user, project=cls.finding.report.project)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + self.uri)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 302)

        self.user.enable_finding_create = True
        self.user.save()
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 302)


class AssignFindingTests(TestCase):
    """Collection of tests for :view:`reporting.AssignFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse(
            "reporting:ajax_assign_finding", kwargs={"pk": cls.finding.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_response_with_session_vars_with_permissions(self):
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = self.report.id
        self.session["active_report"]["title"] = self.report.title
        self.session.save()

        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.id, "title": self.report.title},
        )

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(operator=self.user, project=self.report.project)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_response_with_report_id(self):
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session.save()

        response = self.client_mgr.post(self.uri, data={"report": self.report.id})
        self.assertEqual(response.status_code, 200)

    def test_view_response_with_bad_session_vars(self):
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = 999
        self.session["active_report"]["title"] = self.report.title
        self.session.save()

        self.assertEqual(
            self.session["active_report"],
            {"id": 999, "title": self.report.title},
        )

        response = self.client_mgr.post(self.uri)
        message = "Please select a report to edit in the sidebar or go to a report's dashboard to assign an finding."
        data = {"result": "error", "message": message}

        self.assertJSONEqual(force_str(response.content), data)

    def test_view_response_without_session_vars(self):
        self.session = self.client_mgr.session
        self.session["active_report"] = None
        self.session.save()

        self.assertEqual(self.session["active_report"], None)

        response = self.client_mgr.post(self.uri)
        message = "Please select a report to edit in the sidebar or go to a report's dashboard to assign an finding."
        data = {"result": "error", "message": message}

        self.assertJSONEqual(force_str(response.content), data)

    def test_finding_assigned_to_requesting_user(self):
        response = self.client_mgr.post(self.uri, data={"report": self.report.id})
        self.assertEqual(response.status_code, 200)
        rfl = ReportFindingLink.objects.filter(report=self.report).last()
        self.assertIsNotNone(rfl)
        self.assertEqual(rfl.assigned_to, self.mgr_user)


class ReportCloneTests(TestCase):
    """Collection of tests for :view:`reporting.ReportClone`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.Report = ReportFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.ReportObservationLink = ReportObservationLinkFactory._meta.model
        cls.Evidence = EvidenceFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(
                ReportFindingLinkFactory(title=title, report=cls.report)
            )
        cls.observations = []
        for observation_id in range(cls.num_of_findings):
            title = f"Observation {observation_id}"
            cls.observations.append(
                ReportObservationLinkFactory(title=title, report=cls.report)
            )

        cls.uri = reverse("reporting:report_clone", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("reporting/reports/", response.url)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_report(self):
        uri = reverse("reporting:report_clone", kwargs={"pk": 100})
        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_clone_with_zero_findings_and_observations(self):
        self.ReportFindingLink.objects.all().delete()
        self.ReportObservationLink.objects.all().delete()
        response = self.client_mgr.get(self.uri)
        self.assertIn("reporting/reports/", response.url)

        report_copy = self.Report.objects.latest("id")
        self.assertEqual(report_copy.title, f"{self.report.title} Copy")

        copied_findings = self.ReportFindingLink.objects.filter(report=report_copy)
        self.assertEqual(len(copied_findings), 0)

    def test_clone_with_findings_and_observations(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("reporting/reports/", response.url)

        report_copy = self.Report.objects.latest("id")
        self.assertEqual(report_copy.title, f"{self.report.title} Copy")

        copied_findings = self.ReportFindingLink.objects.filter(report=report_copy)
        self.assertEqual(len(copied_findings), self.num_of_findings)

        copied_observations = self.ReportObservationLink.objects.filter(
            report=report_copy
        )
        self.assertEqual(len(copied_observations), self.num_of_findings)

    def test_clone_with_report_evidence_file(self):
        self.Evidence.objects.all().delete()
        report = ReportFactory()
        evidence = EvidenceFactory(report=report)

        uri = reverse("reporting:report_clone", kwargs={"pk": report.pk})
        response = self.client_mgr.get(uri)
        self.assertIn("reporting/reports/", response.url)

        evidence_files = self.Evidence.objects.filter(
            friendly_name=evidence.friendly_name
        )
        self.assertEqual(len(evidence_files), 2)

        # Check the evidence file was copied to the new report's directory
        report_copy = self.Report.objects.latest("id")
        evidence_copy = evidence_files.latest("id")
        assert os.path.exists(evidence_copy.document.path)
        self.assertIn(
            f"ghostwriter/media/evidence/{report_copy.pk}", evidence_copy.document.path
        )

    def test_clone_with_missing_report_evidence_file(self):
        self.Evidence.objects.all().delete()
        report = ReportFactory()
        evidence = EvidenceFactory(report=report)
        evidence_missing_file = EvidenceFactory(report=report)

        # Delete evidence file
        os.remove(evidence_missing_file.document.path)

        uri = reverse("reporting:report_clone", kwargs={"pk": report.pk})
        response = self.client_mgr.get(uri)
        self.assertIn("reporting/reports/", response.url)

        # Check that the evidence with the missing file was not copied
        evidence_files = self.Evidence.objects.filter(
            friendly_name=evidence.friendly_name
        )
        self.assertEqual(len(evidence_files), 2)
        evidence_files = self.Evidence.objects.filter(
            friendly_name=evidence_missing_file.friendly_name
        )
        self.assertEqual(len(evidence_files), 1)
        # Total = 2 from the original report + 1 from the copy
        self.assertEqual(len(self.Evidence.objects.all()), 3)


# Tests related to :model:`reporting.Finding`


class FindingsListViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingsListView`."""

    @classmethod
    def setUpTestData(cls):
        cls.Finding = FindingFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(FindingFactory(title=title))

        cls.project = ProjectFactory()
        cls.accessibleReport = ReportFactory(project=cls.project)
        _ = ProjectAssignmentFactory(project=cls.project, operator=cls.user)
        cls.accessibleReportFindings = [
            ReportFindingLinkFactory(
                title=f"Report Finding {i}",
                report=cls.accessibleReport,
                added_as_blank=False,
            )
            for i in range(cls.num_of_findings)
        ]
        cls.blankReportFinding = ReportFindingLinkFactory(
            title=f"Report Finding {cls.num_of_findings + 1}",
            added_as_blank=True,
            report=cls.accessibleReport,
        )
        cls.accessibleReportFindings.append(cls.blankReportFinding)

        cls.inaccessibleReport = ReportFactory()
        cls.inaccessibleReportFindings = [
            ReportFindingLinkFactory(
                title=f"Inaccessible Report Finding {i}", report=cls.inaccessibleReport
            )
            for i in range(cls.num_of_findings)
        ]

        cls.uri = reverse("reporting:findings")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_list.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("filter", response.context)
        self.assertIn("autocomplete", response.context)

    def test_lists_all_findings(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.findings))

    def test_search_findings(self):
        response = self.client_auth.get(self.uri + "?finding=Finding+2")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)

    def test_filter_findings(self):
        response = self.client_auth.get(self.uri + "?title=Finding+2&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)

    def test_tags_are_scoped_to_findings(self):
        visible_finding = FindingFactory(title="Tagged Finding")
        visible_finding.tags.add("visible-finding-tag")
        hidden_report = ReportFactory(title="Hidden Tagged Report")
        hidden_report.tags.add("hidden-report-tag")
        hidden_project = ProjectFactory()
        hidden_project.tags.add("hidden-project-tag")

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-finding-tag", tag_names)
        self.assertNotIn("hidden-report-tag", tag_names)
        self.assertNotIn("hidden-project-tag", tag_names)

    def test_search_report_findings(self):
        response = self.client_auth.get(self.uri + "?on_reports=on")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            len(response.context["filter"].qs) == len(self.accessibleReportFindings)
        )

        response = self.client_auth.get(self.uri + "?on_reports=on&not_cloned=on")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)
        blank_findings = self.ReportFindingLink.objects.filter(
            added_as_blank=True, report=self.accessibleReport
        )
        self.assertQuerySetEqual(
            response.context["filter"].qs, list(blank_findings), transform=lambda x: x
        )

    def test_report_finding_tags_are_scoped_to_accessible_report_findings(self):
        self.accessibleReportFindings[0].tags.add("visible-report-finding-tag")
        self.inaccessibleReportFindings[0].tags.add("hidden-report-finding-tag")
        master_finding = FindingFactory(title="Master Tagged Finding")
        master_finding.tags.add("hidden-master-finding-tag")

        response = self.client_auth.get(self.uri + "?on_reports=on")
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-report-finding-tag", tag_names)
        self.assertNotIn("hidden-report-finding-tag", tag_names)
        self.assertNotIn("hidden-master-finding-tag", tag_names)


class FindingDetailViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("reporting:finding_detail", kwargs={"pk": cls.finding.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_detail.html")


class FindingCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingCreate`."""

    @classmethod
    def setUpTestData(cls):
        # Create page assumes that these exist with these IDs
        cls.type = FindingTypeFactory(id=1)
        cls.severity = SeverityFactory(id=1)

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:finding_create")
        cls.failure_redirect_uri = reverse("reporting:findings")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + self.uri)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        self.user.enable_finding_create = True
        self.user.save()
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 302)


class FindingUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:finding_update", kwargs={"pk": cls.finding.pk})
        cls.failure_redirect_uri = reverse("reporting:findings")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        self.user.enable_finding_edit = True
        self.user.save()
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_update.html")

    def test_default_cvss_version_configuration(self):
        """Test that the default CVSS version from ReportConfiguration is passed to the frontend."""
        from ghostwriter.commandcenter.models import ReportConfiguration

        # Get the report configuration singleton
        report_config = ReportConfiguration.get_solo()

        # Capture original value and ensure it's always restored
        original_version = report_config.default_cvss_version
        self.addCleanup(lambda: self._restore_cvss_version(original_version))

        # Test default behavior (should be v3.1)
        self.assertEqual(report_config.default_cvss_version, "3.1")
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        # Check that the default CVSS version is in the context and HTML
        self.assertEqual(response.context["collab_default_cvss_version"], "3.1")
        self.assertContains(
            response, '<script type="text/plain" id="default-cvss-version">3.1</script>'
        )

        # Change the default to v4.0
        report_config.default_cvss_version = "4.0"
        report_config.save()

        # Request the page again
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        # Check that the new default is in the context and HTML
        self.assertEqual(response.context["collab_default_cvss_version"], "4.0")
        self.assertContains(
            response, '<script type="text/plain" id="default-cvss-version">4.0</script>'
        )

    def _restore_cvss_version(self, version):
        """Helper to restore CVSS version in cleanup."""
        from ghostwriter.commandcenter.models import ReportConfiguration

        report_config = ReportConfiguration.get_solo()
        report_config.default_cvss_version = version
        report_config.save()


class FindingDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:finding_delete", kwargs={"pk": cls.finding.pk})
        cls.failure_redirect_uri = reverse(
            "reporting:finding_detail", kwargs={"pk": cls.finding.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        self.user.enable_finding_delete = True
        self.user.save()
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:findings"),
        )
        self.assertEqual(
            response.context["object_type"],
            "finding master record",
        )
        self.assertEqual(response.context["object_to_be_deleted"], self.finding.title)


class FindingExportViewTests(TestCase):
    """Collection of tests for :view:`reporting.export_findings_to_csv`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.num_of_findings = 10
        cls.findings = []
        cls.tags = ["severity:high, att&ck:t1159"]
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(FindingFactory(title=title, tags=cls.tags))
        cls.uri = reverse("reporting:export_findings_to_csv")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv")

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ObservationExportViewTests(TestCase):
    """Collection of tests for :view:`reporting.export_observations_to_csv`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.num_of_observations = 10
        cls.observations = []
        cls.tags = ["severity:high, att&ck:t1159"]
        for observation_id in range(cls.num_of_observations):
            title = f"Observation {observation_id}"
            cls.observations.append(ObservationFactory(title=title, tags=cls.tags))
        cls.uri = reverse("reporting:export_observations_to_csv")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv")

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`reporting.Report`


class ReportsListViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportListView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.num_of_reports = 10
        cls.reports = []
        for report_id in range(cls.num_of_reports):
            title = f"Report {report_id}"
            cls.reports.append(ReportFactory(title=title))

        cls.uri = reverse("reporting:reports")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_list.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("filter", response.context)

    def test_lists_all_reports(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.reports))

    def test_lists_filtered_reports(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 0)

        for report in self.reports[:5]:
            ProjectAssignmentFactory(project=report.project, operator=self.user)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 5)

    def test_tags_are_scoped_to_visible_reports(self):
        visible_report = ReportFactory(title="Visible Report")
        hidden_report = ReportFactory(title="Hidden Report")
        ProjectAssignmentFactory(project=visible_report.project, operator=self.user)
        visible_report.tags.add("visible-report-tag")
        hidden_report.tags.add("hidden-report-tag")

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-report-tag", tag_names)
        self.assertNotIn("hidden-report-tag", tag_names)


class ReportDetailViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})
        cls.failure_redirect_uri = reverse("reporting:reports")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_detail.html")

    def test_view_without_findings_does_not_initialize_severity_sortables(self):
        response = self.client_mgr.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No findings have been added to this report yet.")
        self.assertNotContains(response, "Sortable.create(severity_")
        self.assertNotContains(response, "findings-update-url")

    def test_view_with_findings_initializes_guarded_severity_sortables(self):
        ReportFindingLinkFactory(report=self.report)

        response = self.client_mgr.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="findings-table"')
        self.assertContains(response, "document.getElementById('severity_")
        self.assertContains(response, "Sortable.create(severity_")

    def test_rich_text_extra_field_with_list_value_renders(self):
        report_extra_field_model, _ = ExtraFieldModel.objects.get_or_create(
            model_internal_name="reporting.Report",
            defaults={"model_display_name": "Reports"},
        )
        ExtraFieldSpecFactory(
            internal_name="out_of_scope_activities",
            display_name="Out of Scope Activities",
            type="rich_text",
            target_model=report_extra_field_model,
        )
        self.report.extra_fields = {
            "out_of_scope_activities": ["Denial of Service", "Social Engineering"]
        }
        self.report.save(update_fields=["extra_fields"])

        response = self.client_mgr.get(self.uri)

        self.assertEqual(response.status_code, 200)
        # Rich text previews are now lazy-loaded via AJAX, so the modal body
        # contains a placeholder and a data attribute pointing to the preview
        # endpoint instead of inline-rendered content.
        self.assertContains(response, "data-lazy-richtext-url")
        self.assertContains(response, "extra-field-richtext/out_of_scope_activities")

        # Verify the preview endpoint itself renders the list content
        preview_url = reverse(
            "reporting:report_extra_field_richtext",
            kwargs={"pk": self.report.pk, "extra_field_name": "out_of_scope_activities"},
        )
        preview_response = self.client_mgr.get(preview_url)
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, "Denial of Service")
        self.assertContains(preview_response, "Social Engineering")


class ReportOplogOutlineGenerateTests(TestCase):
    """Collection of tests for :view:`reporting.ReportOplogOutlineGenerate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.oplog = OplogFactory(project=cls.report.project, name="Primary Log")
        cls.other_report = ReportFactory()
        cls.other_oplog = OplogFactory(
            project=cls.other_report.project, name="Other Log"
        )
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:report_generate_oplog_outline",
            kwargs={"pk": cls.report.pk},
        )
        cls.failure_redirect_uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )
        self.report_config = ReportConfiguration.get_solo()
        self.report_config.outline_tags = "report,evidence"
        self.report_config.save()

    def test_view_requires_permission(self):
        response = self.client.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )
        # Anonymous requests may be redirected to login or rejected directly depending
        # on the auth handling path exercised during the larger test suite.
        self.assertIn(response.status_code, (302, 403))

        response = self.client_auth.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_view_rejects_oplog_from_another_project(self):
        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.other_oplog.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_view_returns_empty_list_when_no_matching_entries_exist(self):
        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["blocks"], [])

    def test_view_generates_expected_outline_lines(self):
        first_start = datetime(2024, 5, 1, 14, 0, 0, tzinfo=timezone.utc)
        second_start = datetime(2024, 5, 1, 15, 30, 0, tzinfo=timezone.utc)

        entry_one = OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=first_start,
            tool="Nmap",
            dest_ip="10.0.0.20",
            user_context="NT AUTHORITY\\SYSTEM",
            command="nmap -sV 10.0.0.20",
            output="PORT 80/tcp open http",
            comments="<p><strong>Initial foothold</strong> confirmed.</p>",
            tags=["report"],
        )
        entry_two = OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=second_start,
            tool="",
            dest_ip="",
            user_context="",
            command="",
            output="",
            comments="",
            tags=["evidence"],
        )
        OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 2, 9, 0, 0, tzinfo=timezone.utc),
            tags=["internal"],
        )

        report_evidence = EvidenceFactory(
            report=self.report,
            friendly_name="Alpha",
        )
        finding_evidence = EvidenceFactory(
            report=self.report,
            friendly_name="Bravo",
        )
        foreign_evidence = EvidenceFactory(
            report=self.other_report,
            friendly_name="Foreign",
        )

        OplogEntryEvidenceFactory(oplog_entry=entry_one, evidence=report_evidence)
        OplogEntryEvidenceFactory(oplog_entry=entry_one, evidence=finding_evidence)
        OplogEntryEvidenceFactory(oplog_entry=entry_one, evidence=foreign_evidence)

        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            body["blocks"],
            [
                {
                    "type": "narrative",
                    "timestamp": f"On {dateformat(first_start, settings.DATE_FORMAT)} at 14:00:00 UTC",
                    "tool": "Nmap",
                    "command": "nmap -sV 10.0.0.20",
                    "user_context": "NT AUTHORITY\\SYSTEM",
                    "dest": "10.0.0.20",
                    "has_comments": True,
                },
                {
                    "type": "html",
                    "html": "<p><strong>Initial foothold</strong> confirmed.</p>",
                },
                {"type": "paragraph", "text": "Output:"},
                {"type": "code", "text": "PORT 80/tcp open http"},
                {"type": "paragraph", "text": "{{.ref Alpha}}"},
                {"type": "evidence", "evidence_id": report_evidence.id},
                {"type": "paragraph", "text": "{{.ref Bravo}}"},
                {"type": "evidence", "evidence_id": finding_evidence.id},
                {
                    "type": "narrative",
                    "timestamp": "At 15:30:00 UTC",
                    "tool": "N/A",
                    "command": "",
                    "user_context": "N/A",
                    "dest": "N/A",
                    "has_comments": False,
                },
            ],
        )

    def test_view_includes_entries_matching_configured_exact_tag_case_insensitively(self):
        self.report_config.outline_tags = "Credential"
        self.report_config.save()

        OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 1, 18, 45, 0, tzinfo=timezone.utc),
            tool="Seatbelt",
            dest_ip="10.0.0.25",
            command="",
            output="",
            comments="",
            tags=["CREDENTIAL"],
        )

        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["blocks"]), 1)
        self.assertEqual(response.json()["blocks"][0]["tool"], "Seatbelt")

    def test_view_ignores_recording_text_for_output(self):
        entry = OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 1, 18, 45, 0, tzinfo=timezone.utc),
            tool="Nmap",
            dest_ip="",
            command="<p>hashdump</p>",
            user_context="www-data",
            output="",
            comments="",
            tags=["report"],
        )
        OplogEntryRecordingFactory(oplog_entry=entry, recording_text="recorded output")

        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["blocks"],
            [
                {
                    "type": "narrative",
                    "timestamp": f"On {dateformat(entry.start_date, settings.DATE_FORMAT)} at 18:45:00 UTC",
                    "tool": "Nmap",
                    "command": "hashdump",
                    "user_context": "www-data",
                    "dest": "N/A",
                    "has_comments": False,
                },
            ],
        )

    def test_view_includes_entries_matching_configured_prefix_rule(self):
        self.report_config.outline_tags = "cred*,att&ck:"
        self.report_config.save()

        OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 1, 18, 45, 0, tzinfo=timezone.utc),
            tool="SharpDPAPI",
            dest_ip="10.0.0.25",
            command="",
            output="",
            comments="",
            tags=["Credentials"],
        )
        OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 1, 19, 0, 0, tzinfo=timezone.utc),
            tool="Manual Review",
            dest_ip="10.0.0.25",
            command="",
            output="",
            comments="",
            tags=["ATT&CK:T1555"],
        )

        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["blocks"]), 2)
        self.assertEqual(response.json()["blocks"][0]["tool"], "SharpDPAPI")
        self.assertEqual(response.json()["blocks"][1]["tool"], "Manual Review")

    def test_view_preserves_built_in_outline_tags_when_config_changes(self):
        self.report_config.outline_tags = "credential"
        self.report_config.save()

        OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
            tool="Nmap",
            dest_ip="10.0.0.20",
            command="",
            output="",
            comments="",
            tags=["report"],
        )
        OplogEntryFactory(
            oplog_id=self.oplog,
            start_date=datetime(2024, 5, 1, 15, 0, 0, tzinfo=timezone.utc),
            tool="Mimikatz",
            dest_ip="10.0.0.20",
            command="",
            output="",
            comments="",
            tags=["evidence"],
        )

        response = self.client_mgr.post(
            self.uri,
            data=json.dumps({"oplog_id": self.oplog.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["blocks"]), 2)
        self.assertEqual(response.json()["blocks"][0]["tool"], "Nmap")
        self.assertEqual(response.json()["blocks"][1]["tool"], "Mimikatz")


class ReportCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.Report = ReportFactory._meta.model
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:report_create_no_project")
        cls.project_uri = reverse(
            "reporting:report_create", kwargs={"pk": cls.project.pk}
        )
        cls.success_uri = reverse(
            "reporting:report_detail", kwargs={"pk": cls.report.pk}
        )
        cls.bad_project_uri = reverse("reporting:report_create", kwargs={"pk": 999})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<option value="" selected>-- No Active Projects --</option>',
            response.content.decode(),
        )

        ProjectAssignmentFactory(project=self.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields["project"].queryset), 1)
        self.assertEqual(
            response.context["form"].fields["project"].queryset[0], self.project
        )

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_form.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("reporting:reports"))

    def test_view_uri_with_project_exists_at_desired_location(self):
        response = self.client_mgr.get(self.project_uri)
        self.assertEqual(response.status_code, 200)

    def test_custom_context_changes_for_project(self):
        response = self.client_mgr.get(self.project_uri)
        self.assertIn("project", response.context)
        self.assertEqual(
            response.context["project"],
            self.project,
        )
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.project.pk}),
        )

    def test_form_with_no_active_projects(self):
        self.project.complete = True
        self.project.save()

        response = self.client_mgr.get(self.uri)
        self.assertInHTML(
            '<option value="" selected>-- No Active Projects --</option>',
            response.content.decode(),
        )

        self.project.complete = False
        self.project.save()

    def test_get_success_url_with_session_vars(self):
        # Set up session variables to be clear
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = ""
        self.session["active_report"]["title"] = ""
        self.session.save()

        # Send POST to delete and check if session vars are set
        response = self.client_mgr.post(
            self.uri,
            {
                "title": "New Report Title",
                "project": self.report.project.pk,
                "docx_template": self.report.docx_template.pk,
                "pptx_template": self.report.pptx_template.pk,
            },
        )

        # Get report created from request and check response
        new_report = self.Report.objects.get(title="New Report Title")
        success_uri = reverse("reporting:report_detail", kwargs={"pk": new_report.pk})
        self.assertRedirects(response, success_uri)
        self.session = self.client_mgr.session
        self.assertEqual(
            self.session["active_report"],
            {"id": new_report.pk, "title": f"{new_report.title}"},
        )

    def test_form_with_invalid_project(self):
        response = self.client_mgr.get(self.bad_project_uri)
        self.assertIn("exception", response.context)
        self.assertEqual(
            response.context["exception"], "No Project matches the given query."
        )
        self.assertEqual(response.status_code, 404)


class ReportUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        ReportFactory.create_batch(5)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:report_update", kwargs={"pk": cls.report.pk})
        cls.success_uri = reverse(
            "reporting:report_detail", kwargs={"pk": cls.report.pk}
        )
        cls.failure_redirect_uri = reverse("reporting:reports")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields["project"].queryset), 1)
        self.assertEqual(
            response.context["form"].fields["project"].queryset[0], self.report.project
        )
        self.assertTrue(response.context["form"].fields["project"].disabled)

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields["project"].queryset), 6)
        self.assertFalse(response.context["form"].fields["project"].disabled)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_form.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:report_detail", kwargs={"pk": self.report.pk}),
        )

    def test_get_success_url_with_session_vars(self):
        # Set up session variables to be clear
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = ""
        self.session["active_report"]["title"] = ""
        self.session.save()

        # Send POST to delete and check if session vars are set
        response = self.client_mgr.post(
            self.uri,
            {
                "title": self.report.title,
                "project": self.report.project.pk,
                "docx_template": self.report.docx_template.pk,
                "pptx_template": self.report.pptx_template.pk,
            },
        )
        self.assertRedirects(response, self.success_uri)
        self.session = self.client_mgr.session
        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.pk, "title": f"{self.report.title}"},
        )


class ReportDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.Report = ReportFactory._meta.model
        cls.report = ReportFactory()
        cls.delete_report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:report_delete", kwargs={"pk": cls.report.pk})
        cls.delete_uri = reverse(
            "reporting:report_delete", kwargs={"pk": cls.delete_report.pk}
        )
        cls.success_uri = f"{reverse('rolodex:project_detail', kwargs={'pk': cls.delete_report.project.pk})}#reports"
        cls.failure_redirect_uri = reverse("reporting:reports")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.report.project.pk}),
        )
        self.assertEqual(
            response.context["object_type"],
            "entire report, evidence and all",
        )
        self.assertEqual(response.context["object_to_be_deleted"], self.report.title)

    def test_get_success_url(self):
        # Set session variables to "activate" target report object
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = self.delete_report.id
        self.session["active_report"]["title"] = self.delete_report.title
        self.session.save()

        # Send POST to delete and check if session is now cleared
        response = self.client_mgr.post(self.delete_uri)
        self.session = self.client_mgr.session
        self.assertRedirects(response, self.success_uri)
        self.assertEqual(
            self.session["active_report"],
            {"id": "", "title": ""},
        )


class ReportActivateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportActivate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:ajax_activate_report", kwargs={"pk": cls.report.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_sets_sessions_variables(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.session = self.client_mgr.session
        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.id, "title": self.report.title},
        )

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)


class ReportStatusToggleViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportStatusToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(complete=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:ajax_toggle_report_status", kwargs={"pk": cls.report.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_toggles_value(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

        self.report.refresh_from_db()
        self.assertEqual(self.report.complete, True)

        response = self.client_mgr.post(self.uri)
        self.report.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.report.complete, False)

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)


class ReportDeliveryToggleViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportDeliveryToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(delivered=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:ajax_toggle_report_delivery", kwargs={"pk": cls.report.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_toggles_value(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

        self.report.refresh_from_db()
        self.assertEqual(self.report.delivered, True)

        response = self.client_mgr.post(self.uri)
        self.report.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.report.delivered, False)

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)


# Tests related to :model:`reporting.ReportFindingLink`


class ReportFindingLinkUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportFindingLinkUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )

        cls.high_severity = SeverityFactory(severity="High", weight=1)
        cls.critical_severity = SeverityFactory(severity="Critical", weight=0)

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.new_user = UserFactory(password=PASSWORD)

        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(
                ReportFindingLinkFactory(title=title, report=cls.report)
            )

        cls.uri = reverse("reporting:local_edit", kwargs={"pk": cls.findings[0].pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_finding_link_update.html")

    def test_view_renders_numeric_evidence_report_id(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<script type="text/plain" id="graphql-evidence-report-id">{self.report.pk}</script>',
        )

    def test_default_cvss_version_configuration(self):
        """Test that the default CVSS version from ReportConfiguration is passed to the frontend."""
        from ghostwriter.commandcenter.models import ReportConfiguration

        # Get the report configuration singleton
        report_config = ReportConfiguration.get_solo()

        # Capture original value and ensure it's always restored
        original_version = report_config.default_cvss_version
        self.addCleanup(lambda: self._restore_cvss_version(original_version))

        # Test default behavior (should be v3.1)
        self.assertEqual(report_config.default_cvss_version, "3.1")
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        # Check that the default CVSS version is in the context and HTML
        self.assertEqual(response.context["collab_default_cvss_version"], "3.1")
        self.assertContains(
            response, '<script type="text/plain" id="default-cvss-version">3.1</script>'
        )

        # Change the default to v4.0
        report_config.default_cvss_version = "4.0"
        report_config.save()

        # Request the page again
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        # Check that the new default is in the context and HTML
        self.assertEqual(response.context["collab_default_cvss_version"], "4.0")
        self.assertContains(
            response, '<script type="text/plain" id="default-cvss-version">4.0</script>'
        )

    def _restore_cvss_version(self, version):
        """Helper to restore CVSS version in cleanup."""
        from ghostwriter.commandcenter.models import ReportConfiguration

        report_config = ReportConfiguration.get_solo()
        report_config.default_cvss_version = version
        report_config.save()


# Tests related to :model:`reporting.ReportFindingLink`


class ReportObservationLinkUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportObservationLinkUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )

        cls.high_severity = SeverityFactory(severity="High", weight=1)
        cls.critical_severity = SeverityFactory(severity="Critical", weight=0)

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.new_user = UserFactory(password=PASSWORD)

        cls.num_of_observations = 10
        cls.observations = []
        for observation_id in range(cls.num_of_observations):
            title = f"observation {observation_id}"
            cls.observations.append(
                ReportObservationLinkFactory(title=title, report=cls.report)
            )

        cls.uri = reverse(
            "reporting:local_observation_edit", kwargs={"pk": cls.observations[0].pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reporting/report_observation_link_update.html"
        )

    def test_view_renders_numeric_evidence_report_id(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<script type="text/plain" id="graphql-evidence-report-id">{self.report.pk}</script>',
        )


class ReportExtraFieldEditViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportExtraFieldEdit`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )
        cls.extra_field_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Report",
            model_display_name="Reports",
        )
        cls.extra_field = ExtraFieldSpecFactory(
            internal_name="narrative",
            display_name="Narrative",
            type="rich_text",
            target_model=cls.extra_field_model,
        )
        cls.json_extra_field = ExtraFieldSpecFactory(
            internal_name="json",
            display_name="JSON",
            type="json",
            target_model=cls.extra_field_model,
        )
        cls.report.extra_fields = {
            "json": {"large": ["value", {"nested": "content"}]},
        }
        cls.report.save(update_fields=["extra_fields"])
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:report_extra_field_edit",
            kwargs={
                "pk": cls.report.pk,
                "extra_field_name": cls.extra_field.internal_name,
            },
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_update_extra_field.html")

    def test_view_renders_numeric_evidence_report_id(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<script type="text/plain" id="graphql-evidence-report-id">{self.report.pk}</script>',
        )

    def test_json_extra_field_modal_is_lazy_loaded(self):
        lazy_json_url = reverse(
            "reporting:report_extra_field_json",
            kwargs={
                "pk": self.report.pk,
                "extra_field_name": self.json_extra_field.internal_name,
            },
        )
        rendered = render_to_string(
            "user_extra_fields/extra_field_modal.html",
            {
                "extra_fields": self.report.extra_fields,
                "field_spec": self.json_extra_field,
                "report": self.report,
                "lazy_json_url": lazy_json_url,
            },
        )

        self.assertIn(lazy_json_url, rendered)
        self.assertIn("JSON content will load when this preview opens.", rendered)
        self.assertNotIn("jsonView", rendered)
        self.assertNotIn("nested", rendered)

    def test_report_detail_json_lazy_loader_has_loading_spinner(self):
        response = self.client_mgr.get(reverse("reporting:report_detail", kwargs={"pk": self.report.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "fa-spinner fa-spin")
        self.assertContains(response, "Loading JSON content...")
        self.assertContains(response, "shown.bs.modal")
        self.assertContains(response, "minimumJsonLoadingMs")
        self.assertContains(response, "hide.bs.modal")
        self.assertContains(response, "jsonPreviewPlaceholder")
        self.assertContains(response, "jsonAbortController")

    def test_json_extra_field_endpoint_requires_login_and_permissions(self):
        uri = reverse(
            "reporting:report_extra_field_json",
            kwargs={
                "pk": self.report.pk,
                "extra_field_name": self.json_extra_field.internal_name,
            },
        )

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["field"], "JSON")
        self.assertEqual(
            response.json()["value"],
            {"large": ["value", {"nested": "content"}]},
        )

    def test_json_extra_field_endpoint_rejects_non_json_fields(self):
        uri = reverse(
            "reporting:report_extra_field_json",
            kwargs={
                "pk": self.report.pk,
                "extra_field_name": self.extra_field.internal_name,
            },
        )

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_richtext_preview_endpoint_requires_login_and_permissions(self):
        uri = reverse(
            "reporting:report_extra_field_richtext",
            kwargs={
                "pk": self.report.pk,
                "extra_field_name": self.extra_field.internal_name,
            },
        )

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)

    def test_richtext_preview_endpoint_rejects_non_richtext_fields(self):
        uri = reverse(
            "reporting:report_extra_field_richtext",
            kwargs={
                "pk": self.report.pk,
                "extra_field_name": self.json_extra_field.internal_name,
            },
        )

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_richtext_preview_grants_access_to_assigned_user(self):
        uri = reverse(
            "reporting:report_extra_field_richtext",
            kwargs={
                "pk": self.report.pk,
                "extra_field_name": self.extra_field.internal_name,
            },
        )

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(project=self.report.project, operator=self.user)
        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 200)

    def test_finding_link_richtext_preview_resolves_finding_extra_fields(self):
        """ReportFindingLink specs are registered against Finding, not ReportFindingLink."""
        finding_ef_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Finding",
            model_display_name="Findings",
        )
        ExtraFieldSpecFactory(
            internal_name="finding_notes",
            display_name="Finding Notes",
            type="rich_text",
            target_model=finding_ef_model,
        )
        rfl = ReportFindingLinkFactory(
            report=self.report,
            extra_fields={"finding_notes": "<p>test content</p>"},
        )
        uri = reverse(
            "reporting:reportfindinglink_extra_field_richtext",
            kwargs={"pk": rfl.pk, "extra_field_name": "finding_notes"},
        )

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test content")

    def test_finding_link_richtext_preview_requires_permissions(self):
        finding_ef_model, _ = ExtraFieldModel.objects.get_or_create(
            model_internal_name="reporting.Finding",
            defaults={"model_display_name": "Findings"},
        )
        ExtraFieldSpecFactory(
            internal_name="finding_notes2",
            display_name="Finding Notes 2",
            type="rich_text",
            target_model=finding_ef_model,
        )
        rfl = ReportFindingLinkFactory(
            report=self.report,
            extra_fields={"finding_notes2": "<p>secret</p>"},
        )
        uri = reverse(
            "reporting:reportfindinglink_extra_field_richtext",
            kwargs={"pk": rfl.pk, "extra_field_name": "finding_notes2"},
        )

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)


class ExpandEvidenceAndSanitizeTests(TestCase):
    """Tests for expand_evidence_and_sanitize marker expansion."""

    def test_ref_marker_expanded(self):
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        html = '<p>See <span data-gw-ref="evA"></span> for details</p>'
        result = expand_evidence_and_sanitize(html, None)
        self.assertIn("Figure", result)
        self.assertIn("#", result)
        self.assertNotIn("data-gw-ref", result)

    def test_inline_caption_marker_expanded(self):
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        html = '<p><span data-gw-caption=""></span>My Caption</p>'
        result = expand_evidence_and_sanitize(html, None)
        self.assertIn("Figure", result)
        self.assertIn("My Caption", result)
        self.assertNotIn("data-gw-caption", result)

    def test_block_caption_wrapped_in_p(self):
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        html = '<div data-gw-caption="bookmark">Caption Text</div>'
        result = expand_evidence_and_sanitize(html, None)
        self.assertIn("<p>", result)
        self.assertIn("Caption Text", result)
        self.assertIn("Figure", result)

    def test_image_marker_without_client_decomposed(self):
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        html = '<div data-gw-image="CLIENT_LOGO"></div>'
        result = expand_evidence_and_sanitize(html, None)
        self.assertNotIn("CLIENT_LOGO", result)
        self.assertNotIn("__GW_IMAGE_PREVIEW_", result)

    def test_image_marker_with_client_logo(self):
        from unittest.mock import MagicMock, PropertyMock, patch
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        client = ClientFactory()
        logo_mock = MagicMock()
        logo_mock.__bool__ = lambda s: True
        logo_mock.name = "test_logo.png"
        with patch.object(type(client), "logo", new_callable=PropertyMock, return_value=logo_mock):
            html = '<div data-gw-image="CLIENT_LOGO"></div>'
            result = expand_evidence_and_sanitize(html, None, client=client)
        self.assertIn("<img", result)
        self.assertIn("/rolodex/clients/logo/download/", result)
        self.assertNotIn("__GW_IMAGE_PREVIEW_", result)

    def test_evidence_markers_without_report_decomposed(self):
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        html = '<p><span data-gw-evidence="999"></span></p>'
        result = expand_evidence_and_sanitize(html, None)
        self.assertNotIn("data-gw-evidence", result)

    def test_plain_html_passes_through(self):
        from ghostwriter.commandcenter.templatetags.extra_fields import expand_evidence_and_sanitize
        html = '<p>Hello <strong>world</strong></p>'
        result = expand_evidence_and_sanitize(html, None)
        self.assertIn("Hello", result)
        self.assertIn("world", result)


class ReportFindingLinkPreviewTests(TestCase):
    """Tests for :view:`reporting.ReportFindingLinkPreview`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )
        cls.finding_ef_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Finding",
            model_display_name="Findings",
        )
        cls.finding_rt_field = ExtraFieldSpecFactory(
            internal_name="notes",
            display_name="Finding Notes",
            type="rich_text",
            target_model=cls.finding_ef_model,
        )
        cls.rfl = ReportFindingLinkFactory(
            report=cls.report,
            title="Test Finding",
            description="<p>Finding description</p>",
            extra_fields={"notes": "<p>Extra field content</p>"},
        )
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:finding_preview", kwargs={"pk": cls.rfl.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_unauthorized_user_gets_403(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_manager_gets_200_with_content(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Test Finding", content)
        self.assertIn("Finding description", content)

    def test_renders_severity_badge(self):
        response = self.client_mgr.get(self.uri)
        content = response.content.decode()
        self.assertIn("badge", content)

    def test_renders_extra_field_with_display_name(self):
        response = self.client_mgr.get(self.uri)
        content = response.content.decode()
        self.assertIn("Finding Notes", content)
        self.assertIn("Extra field content", content)

    def test_hr_separator_after_badges(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("<hr>", content)

    def test_empty_fields_omitted(self):
        rfl = ReportFindingLinkFactory(
            report=self.report,
            title="Empty Finding",
            description="",
            impact="",
            mitigation="",
            replication_steps="",
            host_detection_techniques="",
            network_detection_techniques="",
            references="",
        )
        uri = reverse("reporting:finding_preview", kwargs={"pk": rfl.pk})
        response = self.client_mgr.get(uri)
        content = response.content.decode()
        self.assertIn("Empty Finding", content)
        self.assertNotIn("<h3>Description</h3>", content)
        self.assertNotIn("<h3>Impact</h3>", content)

    def test_respects_report_bloodhound_setting(self):
        report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
            include_bloodhound_data=False,
        )
        rfl = ReportFindingLinkFactory(
            report=report,
            title="BloodHound Probe",
            description="{% if bloodhound is defined %}LEAKED{% else %}NO_BH{% endif %}",
        )
        uri = reverse("reporting:finding_preview", kwargs={"pk": rfl.pk})

        response = self.client_mgr.get(uri)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("NO_BH", content)
        self.assertNotIn("LEAKED", content)


class ReportObservationLinkPreviewTests(TestCase):
    """Tests for :view:`reporting.ReportObservationLinkPreview`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )
        cls.obs_ef_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Observation",
            model_display_name="Observations",
        )
        cls.obs_rt_field = ExtraFieldSpecFactory(
            internal_name="obs_notes",
            display_name="Observation Notes",
            type="rich_text",
            target_model=cls.obs_ef_model,
        )
        cls.rol = ReportObservationLinkFactory(
            report=cls.report,
            title="Test Observation",
            description="<p>Observation description</p>",
            extra_fields={"obs_notes": "<p>Observation extra</p>"},
        )
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:observation_preview", kwargs={"pk": cls.rol.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_unauthorized_user_gets_403_html(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_manager_gets_200_with_content(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Test Observation", content)
        self.assertIn("Observation description", content)

    def test_renders_extra_field_with_display_name(self):
        response = self.client_mgr.get(self.uri)
        content = response.content.decode()
        self.assertIn("Observation Notes", content)
        self.assertIn("Observation extra", content)

    def test_no_severity_badges(self):
        response = self.client_mgr.get(self.uri)
        content = response.content.decode()
        self.assertNotIn("badge-pill", content)

    def test_empty_description_omitted(self):
        rol = ReportObservationLinkFactory(
            report=self.report,
            title="Empty Obs",
            description="",
        )
        uri = reverse("reporting:observation_preview", kwargs={"pk": rol.pk})
        response = self.client_mgr.get(uri)
        content = response.content.decode()
        self.assertIn("Empty Obs", content)
        self.assertNotIn("<h3>Description</h3>", content)

    def test_render_export_error_returns_preview_error(self):
        rol = ReportObservationLinkFactory(
            report=self.report,
            title="Bad Regex Obs",
            description="{{ 'content'|regex_search('(') }}",
        )
        uri = reverse("reporting:observation_preview", kwargs={"pk": rol.pk})

        response = self.client_mgr.get(uri)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Bad Regex Obs", content)
        self.assertIn("Preview Error", content)

    def test_respects_report_bloodhound_setting(self):
        report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
            include_bloodhound_data=False,
        )
        rol = ReportObservationLinkFactory(
            report=report,
            title="BloodHound Probe",
            description="{% if bloodhound is defined %}LEAKED{% else %}NO_BH{% endif %}",
        )
        uri = reverse("reporting:observation_preview", kwargs={"pk": rol.pk})

        response = self.client_mgr.get(uri)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("NO_BH", content)
        self.assertNotIn("LEAKED", content)


class ExtraFieldRichTextPreviewPermissionTests(TestCase):
    """Tests for ExtraFieldRichTextPreviewView permission handling."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )
        cls.extra_field_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Report",
            model_display_name="Reports",
        )
        cls.rt_field = ExtraFieldSpecFactory(
            internal_name="test_rt",
            display_name="Test RT",
            type="rich_text",
            target_model=cls.extra_field_model,
        )
        cls.report.extra_fields = {"test_rt": "<p>content</p>"}
        cls.report.save(update_fields=["extra_fields"])
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:report_extra_field_richtext",
            kwargs={"pk": cls.report.pk, "extra_field_name": "test_rt"},
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_403_returns_html_not_json(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Content-Type"], "text/html")
        self.assertIn("permission", response.content.decode())

    def test_nonexistent_field_returns_404(self):
        uri = reverse(
            "reporting:report_extra_field_richtext",
            kwargs={"pk": self.report.pk, "extra_field_name": "nonexistent"},
        )
        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_template_error_returns_200_with_error_message(self):
        self.report.extra_fields = {"test_rt": "<p>{% for x in %}broken{% endfor %}</p>"}
        self.report.save(update_fields=["extra_fields"])
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Error", content)
        self.assertIn("alert-danger", content)


# Tests related to :model:`reporting.Evidence`


class EvidenceDetailViewTests(TestCase):
    """
    Collection of tests for :view:`reporting.EvidenceDetailView` and the related
    :view:`reporting.upload_evidence_modal_success`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.img_evidence = EvidenceFactory(img=True)
        cls.txt_evidence = EvidenceFactory(txt=True)
        cls.unknown_evidence = EvidenceFactory(unknown=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.img_uri = reverse(
            "reporting:evidence_detail", kwargs={"pk": cls.img_evidence.pk}
        )
        cls.txt_uri = reverse(
            "reporting:evidence_detail", kwargs={"pk": cls.txt_evidence.pk}
        )
        cls.unknown_uri = reverse(
            "reporting:evidence_detail", kwargs={"pk": cls.unknown_evidence.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.img_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.img_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.img_uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(
            project=self.img_evidence.report.project, operator=self.user
        )
        response = self.client_auth.get(self.img_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.img_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_detail.html")


class BaseEvidenceCreateViewTests:
    """
    Base collection of tests for :view:`reporting.EvidenceCreate`.

    Does not inherit from TestCase so that this isn't ran as a test case
    """

    @classmethod
    def setupEvidenceFactory(cls):
        """Returns a tuple of the evidence factory and the ID of the parent report"""
        raise NotImplementedError()

    @classmethod
    def setUpTestData(cls):
        (evidence, parent_pk) = cls.setupEvidenceFactory()
        cls.evidence = evidence
        cls.parent_pk = parent_pk
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:upload_evidence", kwargs={"pk": parent_pk})
        cls.modal_uri = reverse(
            "reporting:upload_evidence_modal",
            kwargs={"pk": parent_pk, "modal": "modal"},
        )
        cls.success_uri = reverse(
            "reporting:report_detail", args=(cls.evidence.report.pk,)
        )
        cls.modal_success_uri = reverse("reporting:upload_evidence_modal_success")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    # Testing regular form view
    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_form.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            f"{reverse('reporting:report_detail', kwargs={'pk': self.evidence.report.pk})}#evidence",
        )

    # Testing modal form view
    def test_view_modal_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.modal_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_modal_requires_login_and_permissions(self):
        response = self.client.get(self.modal_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.modal_uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(
            project=self.evidence.report.project, operator=self.user
        )
        response = self.client_auth.get(self.modal_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_modal_uses_correct_template(self):
        response = self.client_mgr.get(self.modal_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_form_modal.html")

    def test_custom_modal_context_exists(self):
        response = self.client_mgr.get(self.modal_uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("used_friendly_names", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            f"{reverse('reporting:report_detail', kwargs={'pk': self.evidence.report.pk})}#evidence",
        )

    def test_json_upload_creates_evidence_for_editor_modal(self):
        ProjectAssignmentFactory(
            project=self.evidence.report.project, operator=self.user
        )
        upload = SimpleUploadedFile(
            "collab-evidence.txt", b"evidence body", content_type="text/plain"
        )

        response = self.client_auth.post(
            self.modal_uri,
            data={
                "friendly_name": "Collab Evidence",
                "document": upload,
                "description": "",
                "caption": "Collab evidence caption",
                "tags": "",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        created = Evidence.objects.get(pk=response.json()["pk"])
        self.assertEqual(created.uploaded_by, self.user)
        self.assertEqual(created.friendly_name, "Collab Evidence")
        self.assertEqual(created.caption, "Collab evidence caption")
        self.assertEqual(created.report_id, self.parent_pk)

    # Testing modal success view
    def test_view_modal_success_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.modal_success_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_modal_success_requires_login(self):
        response = self.client.get(self.modal_success_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_modal_success_uses_correct_template(self):
        response = self.client_mgr.get(self.modal_success_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_modal_success.html")


class EvidenceForReportCreateViewTests(BaseEvidenceCreateViewTests, TestCase):
    """Collection of tests for :view:`reporting.EvidenceCreate`."""

    @classmethod
    def setupEvidenceFactory(cls):
        cls.report = ReportFactory()
        evidence = EvidenceFactory(report=cls.report)
        return (evidence, evidence.report.pk)


class EvidenceUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.EvidenceUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.evidence = EvidenceFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:evidence_update", kwargs={"pk": cls.evidence.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(
            operator=self.user, project=self.evidence.report.project
        )
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_form.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:evidence_detail", kwargs={"pk": self.evidence.pk}),
        )


class EvidenceDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.EvidenceDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.evidence = EvidenceFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = f"{reverse('reporting:evidence_delete', kwargs={'pk': cls.evidence.pk})}#evidence"

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(
            operator=self.user, project=self.evidence.report.project
        )
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            f"{reverse('reporting:report_detail', kwargs={'pk': self.evidence.report.pk})}#evidence",
        )
        self.assertEqual(
            response.context["object_type"],
            "evidence file (and associated file on disk)",
        )
        self.assertEqual(
            response.context["object_to_be_deleted"], self.evidence.friendly_name
        )


# Tests related to :model:`reporting.ReportTemplate`


class ReportTemplateListViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateListView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.template_client = ClientFactory(name="SpecterOps")

        cls.DocType = DocTypeFactory._meta.model
        cls.ReportTemplate = ReportTemplateFactory._meta.model

        cls.ReportTemplate.objects.all().delete()
        cls.DocType.objects.all().delete()

        docx_type = DocTypeFactory(doc_type="docx", extension="docx", name="docx", id=1)
        pptx_type = DocTypeFactory(doc_type="pptx", extension="pptx", name="pptx", id=2)

        cls.num_of_templates = 5
        cls.templates = []
        for template_id in range(cls.num_of_templates):
            cls.templates.append(ReportTemplateFactory(docx=True, doc_type=docx_type))
            cls.templates.append(ReportTemplateFactory(pptx=True, doc_type=pptx_type))
        cls.templates.append(
            ReportTemplateFactory(
                client=cls.template_client,
                tags=["tag1"],
                name="Filtered",
                doc_type=docx_type,
            )
        )

        cls.uri = reverse("reporting:templates")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs), self.num_of_templates)

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs), self.num_of_templates + 1)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_templates_list.html")

    def test_template_filtering(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 10)

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 11)

        response = self.client_mgr.get(f"{self.uri}?name=filtered")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)

        response = self.client_auth.get(f"{self.uri}?doc_type=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 5)

        response = self.client_auth.get(f"{self.uri}?doc_type=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 5)

        response = self.client_auth.get(f"{self.uri}?client=spec")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 0)

        response = self.client_mgr.get(f"{self.uri}?client=spec")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)

        response = self.client_mgr.get(f"{self.uri}?tags=tag1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)


class ReportTemplateDownloadTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateDownload`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.assigned_user = UserFactory(password=PASSWORD)
        cls.template_client = ClientFactory()
        cls.scoped_template = ReportTemplateFactory(
            client=cls.template_client, protected=True
        )
        ProjectAssignmentFactory(
            project=ProjectFactory(client=cls.template_client),
            operator=cls.assigned_user,
        )
        cls.uri = reverse("reporting:template_download", kwargs={"pk": cls.template.pk})
        cls.scoped_uri = reverse(
            "reporting:template_download", kwargs={"pk": cls.scoped_template.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_assigned = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_assigned.login(
                username=self.assigned_user.username, password=PASSWORD
            )
        )

    def test_view_uri_returns_desired_download(self):
        """Test default behavior downloads file (as_attachment=True)."""
        response = self.client_auth.get(f"{self.uri}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            f'attachment; filename="{self.template.filename}"',
        )
        # Verify security header is present
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

    def test_view_inline_with_view_parameter(self):
        """Test inline viewing with ?view=true parameter."""
        response = self.client_auth.get(f"{self.uri}?view=true")
        self.assertEqual(response.status_code, 200)
        # Should NOT have attachment disposition for inline viewing
        content_disposition = response.get("Content-Disposition")
        if content_disposition:
            self.assertNotIn("attachment", content_disposition)
        # Verify security headers
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("Content-Security-Policy", response)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_denies_client_scoped_template_without_access(self):
        response = self.client_auth.get(self.scoped_uri)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("reporting:templates"))

    def test_view_allows_client_scoped_template_with_access(self):
        response = self.client_assigned.get(self.scoped_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            f'attachment; filename="{self.scoped_template.filename}"',
        )


class ReportTemplateDetailViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory(protected=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.admin_user = UserFactory(password=PASSWORD, role="admin")
        cls.uri = reverse("reporting:template_detail", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_admin = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_admin.login(
                username=self.admin_user.username, password=PASSWORD
            )
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_detail.html")

    def test_view_for_protected_template(self):
        response = self.client_auth.get(self.uri)
        self.assertInHTML(
            '<div class="alert alert-danger icon lock-icon" role="alert">This template is protected – only admins and managers may edit it.</div>',
            response.content.decode(),
        )

        response = self.client_admin.get(self.uri)
        self.assertInHTML(
            '<div class="alert alert-secondary icon unlock-icon" role="alert">You may edit this protected template.</div>',
            response.content.decode(),
        )


class ReportTemplateCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:template_create")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"], reverse("reporting:templates")
        )

    def test_initial_form_values(self):
        response = self.client_auth.get(self.uri)

        date = datetime.now().strftime("%d %B %Y")
        initial_upload = f'<p><span class="bold">{date}</span></p><p>Initial upload</p>'

        self.assertEqual(response.context["form"].initial["changelog"], initial_upload)


class ReportTemplateUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory(protected=True)
        cls.template_client = ClientFactory()
        cls.scoped_template = ReportTemplateFactory(
            client=cls.template_client, protected=False
        )
        cls.protected_scoped_template = ReportTemplateFactory(
            client=cls.template_client, protected=True
        )
        cls.user = UserFactory(password=PASSWORD)
        cls.assigned_user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.admin_user = UserFactory(password=PASSWORD, role="admin")
        ProjectAssignmentFactory(
            project=ProjectFactory(client=cls.template_client),
            operator=cls.assigned_user,
        )
        cls.uri = reverse("reporting:template_update", kwargs={"pk": cls.template.pk})
        cls.scoped_uri = reverse(
            "reporting:template_update", kwargs={"pk": cls.scoped_template.pk}
        )
        cls.protected_scoped_uri = reverse(
            "reporting:template_update",
            kwargs={"pk": cls.protected_scoped_template.pk},
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_assigned = Client()
        self.client_mgr = Client()
        self.client_admin = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_assigned.login(
                username=self.assigned_user.username, password=PASSWORD
            )
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_admin.login(
                username=self.admin_user.username, password=PASSWORD
            )
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_form.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"], reverse("reporting:templates")
        )

    def test_view_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_admin.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_denies_client_scoped_template_without_access(self):
        response = self.client_auth.get(self.scoped_uri)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("reporting:templates"))

    def test_view_allows_client_scoped_template_with_access(self):
        response = self.client_assigned.get(self.scoped_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_form.html")

    def test_view_protected_client_scoped_template_requires_privileged_user(self):
        response = self.client_assigned.get(self.protected_scoped_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_mgr.get(self.protected_scoped_uri)
        self.assertEqual(response.status_code, 200)


class ReportTemplateDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory(protected=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.admin_user = UserFactory(password=PASSWORD, role="admin")
        cls.uri = reverse("reporting:template_delete", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_admin = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_admin.login(
                username=self.admin_user.username, password=PASSWORD
            )
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:template_detail", kwargs={"pk": self.template.pk}),
        )
        self.assertEqual(
            response.context["object_type"],
            "report template file (and associated file on disk)",
        )
        self.assertEqual(
            response.context["object_to_be_deleted"], self.template.filename
        )

    def test_view_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_admin.get(self.uri)
        self.assertEqual(response.status_code, 200)


class ReportTemplateLintViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateLint`."""

    @classmethod
    def setUpTestData(cls):
        cls.docx_template = ReportDocxTemplateFactory()
        cls.pptx_template = ReportPptxTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.docx_uri = reverse(
            "reporting:ajax_lint_report_template", kwargs={"pk": cls.docx_template.pk}
        )
        cls.pptx_uri = reverse(
            "reporting:ajax_lint_report_template", kwargs={"pk": cls.pptx_template.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        data = {
            "result": "success",
            "warnings": [],
            "errors": [],
            "message": "Template linter returned results with no errors or warnings.",
        }

        response = self.client_auth.get(self.docx_uri)
        self.assertEqual(response.status_code, 405)

        response = self.client_auth.post(self.docx_uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        response = self.client_auth.post(self.pptx_uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_view_requires_login(self):
        response = self.client.get(self.docx_uri)
        self.assertEqual(response.status_code, 302)

    def test_linting_with_bad_style(self):
        data = {
            "result": "warning",
            "warnings": [
                "Template is missing your configured default paragraph style: bad_style"
            ],
            "errors": [],
            "message": "Template linter returned results with issues that require attention.",
        }

        self.docx_template.p_style = "bad_style"
        self.docx_template.save()
        response = self.client_auth.post(self.docx_uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)
        self.docx_template.p_style = "Normal"
        self.docx_template.save()

    def test_view_denies_client_scoped_template_without_access(self):
        scoped_template = ReportDocxTemplateFactory(client=ClientFactory())
        uri = reverse(
            "reporting:ajax_lint_report_template", kwargs={"pk": scoped_template.pk}
        )
        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 403)

    def test_view_allows_client_scoped_template_with_access(self):
        scoped_client = ClientFactory()
        scoped_template = ReportDocxTemplateFactory(client=scoped_client)
        ProjectAssignmentFactory(
            project=ProjectFactory(client=scoped_client), operator=self.user
        )
        uri = reverse(
            "reporting:ajax_lint_report_template", kwargs={"pk": scoped_template.pk}
        )
        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)


class UpdateTemplateLintResultsViewTests(TestCase):
    """Collection of tests for :view:`reporting.UpdateTemplateLintResults`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse(
            "reporting:ajax_update_template_lint_results",
            kwargs={"pk": cls.template.pk},
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_returns_desired_download(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_denies_client_scoped_template_without_access(self):
        scoped_template = ReportTemplateFactory(client=ClientFactory())
        uri = reverse(
            "reporting:ajax_update_template_lint_results",
            kwargs={"pk": scoped_template.pk},
        )
        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

    def test_view_allows_client_scoped_template_with_access(self):
        scoped_client = ClientFactory()
        scoped_template = ReportTemplateFactory(client=scoped_client)
        ProjectAssignmentFactory(
            project=ProjectFactory(client=scoped_client), operator=self.user
        )
        uri = reverse(
            "reporting:ajax_update_template_lint_results",
            kwargs={"pk": scoped_template.pk},
        )
        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 200)


class ReportTemplateSwapViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateSwap`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.docx_template = ReportDocxTemplateFactory()
        cls.pptx_template = ReportPptxTemplateFactory()

        cls.docx_template_warning = ReportDocxTemplateFactory()
        cls.docx_template_warning.lint_result = {
            "result": "warning",
            "warnings": [],
            "errors": [],
        }
        cls.docx_template_warning.save()
        cls.pptx_template_warning = ReportPptxTemplateFactory()
        cls.pptx_template_warning.lint_result = {
            "result": "warning",
            "warnings": [],
            "errors": [],
        }
        cls.pptx_template_warning.save()

        cls.docx_template_error = ReportDocxTemplateFactory()
        cls.docx_template_error.lint_result = {
            "result": "error",
            "warnings": [],
            "errors": [],
        }
        cls.docx_template_error.save()
        cls.pptx_template_error = ReportPptxTemplateFactory()
        cls.pptx_template_error.lint_result = {
            "result": "error",
            "warnings": [],
            "errors": [],
        }
        cls.pptx_template_error.save()

        cls.docx_template_failed = ReportDocxTemplateFactory()
        cls.docx_template_failed.lint_result = {
            "result": "failed",
            "warnings": [],
            "errors": [],
        }
        cls.docx_template_failed.save()
        cls.pptx_template_failed = ReportPptxTemplateFactory()
        cls.pptx_template_failed.lint_result = {
            "result": "failed",
            "warnings": [],
            "errors": [],
        }
        cls.pptx_template_failed.save()

        cls.docx_template_unknown = ReportDocxTemplateFactory()
        cls.docx_template_unknown.lint_result = {
            "result": "unknown",
            "warnings": [],
            "errors": [],
        }
        cls.docx_template_unknown.save()
        cls.pptx_template_unknown = ReportPptxTemplateFactory()
        cls.pptx_template_unknown.lint_result = {
            "result": "unknown",
            "warnings": [],
            "errors": [],
        }
        cls.pptx_template_unknown.save()

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:ajax_swap_report_template", kwargs={"pk": cls.report.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_valid_templates(self):
        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "docx_lint_result": "success",
            "pptx_lint_result": "success",
            "warnings": [],
        }
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.docx_template.pk,
                "pptx_template": self.pptx_template.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        # Test a negative value indicating no template is selected
        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "pptx_lint_result": "success",
            "warnings": [],
        }
        response = self.client_mgr.post(
            self.uri, {"docx_template": -5, "pptx_template": self.pptx_template.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_invalid_templates(self):
        data = {
            "result": "error",
            "message": "Submitted template ID was not an integer.",
        }
        response = self.client_mgr.post(
            self.uri, {"docx_template": "C", "pptx_template": self.pptx_template.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "error",
            "message": "Submitted template ID does not exist.",
        }
        response = self.client_mgr.post(
            self.uri, {"docx_template": 1000, "pptx_template": self.pptx_template.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {"result": "error", "message": "Submitted request was incomplete."}
        response = self.client_mgr.post(
            self.uri, {"docx_template": "", "pptx_template": self.pptx_template.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_denies_client_scoped_templates_for_other_clients(self):
        foreign_client = ClientFactory()
        foreign_docx_template = ReportDocxTemplateFactory(client=foreign_client)
        foreign_pptx_template = ReportPptxTemplateFactory(client=foreign_client)

        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": foreign_docx_template.pk,
                "pptx_template": foreign_pptx_template.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {"result": "error", "message": "Submitted template ID does not exist."},
        )
        self.report.refresh_from_db()
        self.assertNotEqual(self.report.docx_template_id, foreign_docx_template.pk)
        self.assertNotEqual(self.report.pptx_template_id, foreign_pptx_template.pk)

    def test_denies_templates_for_wrong_document_type(self):
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.pptx_template.pk,
                "pptx_template": self.docx_template.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {"result": "error", "message": "Submitted template ID does not exist."},
        )
        self.report.refresh_from_db()
        self.assertNotEqual(self.report.docx_template_id, self.pptx_template.pk)
        self.assertNotEqual(self.report.pptx_template_id, self.docx_template.pk)

    def test_allows_client_scoped_templates_for_report_client(self):
        docx_template = ReportDocxTemplateFactory(client=self.report.project.client)
        pptx_template = ReportPptxTemplateFactory(client=self.report.project.client)

        response = self.client_mgr.post(
            self.uri,
            {"docx_template": docx_template.pk, "pptx_template": pptx_template.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "success")
        self.report.refresh_from_db()
        self.assertEqual(self.report.docx_template_id, docx_template.pk)
        self.assertEqual(self.report.pptx_template_id, pptx_template.pk)

    def test_allows_templates_with_mixed_case_document_types(self):
        docx_type = DocTypeFactory(doc_type="DoCx", extension="docx", name="DoCx")
        pptx_type = DocTypeFactory(doc_type="PpTx", extension="pptx", name="PpTx")
        docx_template = ReportTemplateFactory(doc_type=docx_type)
        pptx_template = ReportTemplateFactory(doc_type=pptx_type)

        response = self.client_mgr.post(
            self.uri,
            {"docx_template": docx_template.pk, "pptx_template": pptx_template.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "success")
        self.report.refresh_from_db()
        self.assertEqual(self.report.docx_template_id, docx_template.pk)
        self.assertEqual(self.report.pptx_template_id, pptx_template.pk)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(operator=self.user, project=self.report.project)
        response = self.client_auth.post(
            self.uri,
            {
                "docx_template": self.docx_template.pk,
                "pptx_template": self.pptx_template.pk,
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_templates_with_linting_errors(self):
        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "docx_lint_result": "warning",
            "docx_lint_message": "Selected Word template has warnings from linter. Check the template before generating a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_warning.pk}",
            "pptx_lint_result": "warning",
            "pptx_lint_message": "Selected PowerPoint template has warnings from linter. Check the template before generating a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_warning.pk}",
            "warnings": [],
        }
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.docx_template_warning.pk,
                "pptx_template": self.pptx_template_warning.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "docx_lint_result": "error",
            "docx_lint_message": "Selected Word template has linting errors and cannot be used to generate a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_error.pk}",
            "pptx_lint_result": "error",
            "pptx_lint_message": "Selected PowerPoint template has linting errors and cannot be used to generate a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_error.pk}",
            "warnings": [],
        }
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.docx_template_error.pk,
                "pptx_template": self.pptx_template_error.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "docx_lint_result": "failed",
            "docx_lint_message": "Selected Word template failed basic linter checks and can't be used to generate a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_failed.pk}",
            "pptx_lint_result": "failed",
            "pptx_lint_message": "Selected PowerPoint template failed basic linter checks and can't be used to generate a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_failed.pk}",
            "warnings": [],
        }
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.docx_template_failed.pk,
                "pptx_template": self.pptx_template_failed.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "docx_lint_result": "unknown",
            "docx_lint_message": "Selected Word template has an unknown linter status. Check and lint the template before generating a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_unknown.pk}",
            "pptx_lint_result": "unknown",
            "pptx_lint_message": "Selected PowerPoint template has an unknown linter status. Check and lint the template before generating a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_unknown.pk}",
            "warnings": [],
        }
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.docx_template_unknown.pk,
                "pptx_template": self.pptx_template_unknown.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_bloodhound_data_checks(self):
        self.docx_template.contains_bloodhound_data = True
        self.docx_template.save()
        self.pptx_template.contains_bloodhound_data = True
        self.pptx_template.save()
        self.report.project.include_bloodhound_data = False
        self.report.project.save()

        data = {
            "result": "success",
            "message": "Template configuraton successfully updated.",
            "docx_lint_result": "success",
            "pptx_lint_result": "success",
            "warnings": [
                "The selected Word template references BloodHound data, but BloodHound data inclusion is disabled. The report may not generate properly unless the template checks for data existence.",
                "The selected PowerPoint template references BloodHound data, but BloodHound data inclusion is disabled. The report may not generate properly unless the template checks for data existence.",
            ],
        }
        response = self.client_mgr.post(
            self.uri,
            {
                "docx_template": self.docx_template.pk,
                "pptx_template": self.pptx_template.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)


# Tests related to generating report types


class GenerateReportTests(TestCase):
    """Collection of tests for all :view:`reporting.GenerateReport*`."""

    @classmethod
    def setUpTestData(cls):
        cls.org, cls.project, cls.report = GenerateMockProject()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:report_delete", kwargs={"pk": cls.report.pk})
        cls.redirect_uri = reverse(
            "reporting:report_detail", kwargs={"pk": cls.report.pk}
        )
        cls.docx_uri = reverse("reporting:generate_docx", kwargs={"pk": cls.report.pk})
        cls.xlsx_uri = reverse("reporting:generate_xlsx", kwargs={"pk": cls.report.pk})
        cls.pptx_uri = reverse("reporting:generate_pptx", kwargs={"pk": cls.report.pk})
        cls.json_uri = reverse("reporting:generate_json", kwargs={"pk": cls.report.pk})
        cls.all_uri = reverse("reporting:generate_all", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def _xlsx_header_values(self, response):
        return self._xlsx_rows(response)[0]

    def _xlsx_column_index(self, cell_reference):
        column_letters = "".join(char for char in cell_reference if char.isalpha())
        column_index = 0
        for char in column_letters:
            column_index = column_index * 26 + ord(char) - ord("A") + 1
        return column_index - 1

    def _xlsx_rows(self, response):
        with zipfile.ZipFile(io.BytesIO(response.content)) as workbook:
            namespace = {
                "xlsx": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            shared_strings = ElementTree.fromstring(
                workbook.read("xl/sharedStrings.xml")
            )
            strings = [
                "".join(
                    text.text or "" for text in item.findall(".//xlsx:t", namespace)
                )
                for item in shared_strings.findall("xlsx:si", namespace)
            ]
            sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))

            rows = []
            for row in sheet.findall(".//xlsx:sheetData/xlsx:row", namespace):
                row_values = []
                for cell in row.findall("xlsx:c", namespace):
                    column_index = self._xlsx_column_index(cell.get("r"))
                    while len(row_values) <= column_index:
                        row_values.append("")

                    value = cell.find("xlsx:v", namespace)
                    if value is None:
                        row_values[column_index] = ""
                    elif cell.get("t") == "s":
                        row_values[column_index] = strings[int(value.text)]
                    else:
                        row_values[column_index] = value.text
                rows.append(row_values)
        return rows

    def _xlsx_cell_fill_colors(self, response):
        with zipfile.ZipFile(io.BytesIO(response.content)) as workbook:
            namespace = {
                "xlsx": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            styles = ElementTree.fromstring(workbook.read("xl/styles.xml"))

            fills = []
            for fill in styles.findall(".//xlsx:fills/xlsx:fill", namespace):
                color = None
                pattern = fill.find("xlsx:patternFill", namespace)
                if pattern is not None:
                    fg_color = pattern.find("xlsx:fgColor", namespace)
                    if fg_color is not None:
                        color = fg_color.get("rgb")
                fills.append(color)

            style_fill_ids = []
            for style in styles.findall(".//xlsx:cellXfs/xlsx:xf", namespace):
                style_fill_ids.append(int(style.get("fillId", 0)))

            sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
            cell_colors = {}
            for cell in sheet.findall(".//xlsx:sheetData/xlsx:row/xlsx:c", namespace):
                style_index = int(cell.get("s", 0))
                fill_id = style_fill_ids[style_index]
                cell_colors[cell.get("r")] = fills[fill_id]
        return cell_colors

    def test_view_json_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.json_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_docx_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.docx_uri)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.get("Content-Type"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_view_xlsx_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.xlsx_uri)
        self.assertEqual(
            response.get("Content-Type"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_view_xlsx_uses_each_findings_severity_color(self):
        red = SeverityFactory(severity="XLSX Red", color="FF0000")
        green = SeverityFactory(severity="XLSX Green", color="00FF00")
        red_finding = ReportFindingLinkFactory(
            report=self.report, severity=red, title="XLSX Red Finding"
        )
        green_finding = ReportFindingLinkFactory(
            report=self.report, severity=green, title="XLSX Green Finding"
        )

        response = self.client_mgr.get(self.xlsx_uri)
        self.assertEqual(response.status_code, 200, response.content)

        rows = self._xlsx_rows(response)
        red_row_number = next(
            index + 1 for index, row in enumerate(rows) if row[0] == red_finding.title
        )
        green_row_number = next(
            index + 1 for index, row in enumerate(rows) if row[0] == green_finding.title
        )
        cell_colors = self._xlsx_cell_fill_colors(response)

        self.assertTrue(cell_colors[f"B{red_row_number}"].endswith(red.color))
        self.assertTrue(cell_colors[f"C{red_row_number}"].endswith(red.color))
        self.assertTrue(cell_colors[f"D{red_row_number}"].endswith(red.color))
        self.assertTrue(cell_colors[f"B{green_row_number}"].endswith(green.color))
        self.assertTrue(cell_colors[f"C{green_row_number}"].endswith(green.color))
        self.assertTrue(cell_colors[f"D{green_row_number}"].endswith(green.color))

    def test_view_xlsx_populates_supporting_evidence_column(self):
        evidence = EvidenceFactory(
            report=self.report, friendly_name="XLSX Linked Evidence"
        )
        finding = ReportFindingLinkFactory(
            report=self.report,
            title="Finding with XLSX evidence",
            description=f"<p>{{{{.{evidence.friendly_name}}}}}</p>",
            impact=f"<p>{{{{.ref {evidence.friendly_name}}}}}</p>",
            mitigation=f"<p>{{{{.caption {evidence.friendly_name}}}}}</p>",
            replication_steps=f'<div class="richtext-evidence" data-evidence-id="{evidence.pk}"></div>',
        )
        response = self.client_mgr.get(self.xlsx_uri)
        self.assertEqual(response.status_code, 200, response.content)

        expected_headers = [
            "Finding",
            "Severity",
            "CVSS Score",
            "CVSS Vector",
            "Affected Entities",
            "Description",
            "Impact",
            "Recommendation",
            "Replication Steps",
            "Host Detection Techniques",
            "Network Detection Techniques",
            "References",
            "Supporting Evidence",
            "Tags",
        ]
        rows = self._xlsx_rows(response)
        headers = rows[0]
        finding_row = next(row for row in rows[1:] if row[0] == finding.title)

        self.assertEqual(headers[: len(expected_headers)], expected_headers)
        self.assertEqual(
            finding_row[headers.index("Supporting Evidence")], evidence.friendly_name
        )

    def test_view_pptx_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.pptx_uri)
        self.assertEqual(
            response.get("Content-Type"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            repr(response)
            + repr([str(msg) for msg in get_messages(response.wsgi_request)]),
        )

    def test_view_all_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.all_uri)
        self.assertEqual(response.status_code, 200, str(response))
        self.assertEqual(
            response.get("Content-Type"), "application/x-zip-compressed", str(response)
        )

    def test_view_json_requires_login_and_permissions(self):
        response = self.client.get(self.json_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.json_uri)
        self.assertEqual(response.status_code, 302)

        assignment = ProjectAssignmentFactory(
            project=self.report.project, operator=self.user
        )
        response = self.client_auth.get(self.json_uri)
        self.assertEqual(response.status_code, 200)
        assignment.delete()

    def test_view_json_missing_report_requires_login_without_crashing(self):
        missing_uri = reverse("reporting:generate_json", kwargs={"pk": 999999})
        response = self.client.get(missing_uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + missing_uri)

    def test_view_json_missing_report_redirects_authenticated_user(self):
        missing_uri = reverse("reporting:generate_json", kwargs={"pk": 999999})
        response = self.client_mgr.get(missing_uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home:dashboard"))

    def test_view_docx_requires_login_and_permissions(self):
        response = self.client.get(self.docx_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.docx_uri)
        self.assertEqual(response.status_code, 302)

        assignment = ProjectAssignmentFactory(
            project=self.report.project, operator=self.user
        )
        response = self.client_auth.get(self.docx_uri)
        self.assertEqual(response.status_code, 200)
        assignment.delete()

    def test_view_xlsx_requires_login_and_permissions(self):
        response = self.client.get(self.xlsx_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.xlsx_uri)
        self.assertEqual(response.status_code, 302)

        assignment = ProjectAssignmentFactory(
            project=self.report.project, operator=self.user
        )
        response = self.client_auth.get(self.xlsx_uri)
        self.assertEqual(response.status_code, 200)
        assignment.delete()

    def test_view_pptx_requires_login_and_permissions(self):
        response = self.client.get(self.pptx_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.pptx_uri)
        self.assertEqual(response.status_code, 302)

        assignment = ProjectAssignmentFactory(
            project=self.report.project, operator=self.user
        )
        response = self.client_auth.get(self.pptx_uri)
        self.assertEqual(response.status_code, 200)
        assignment.delete()

    def test_view_all_requires_login_and_permissions(self):
        response = self.client.get(self.all_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.all_uri)
        self.assertEqual(response.status_code, 302)

        assignment = ProjectAssignmentFactory(
            project=self.report.project, operator=self.user
        )
        response = self.client_auth.get(self.all_uri)
        self.assertEqual(response.status_code, 200, str(response.request))
        assignment.delete()

    def test_generation_denies_client_scoped_template_for_other_client(self):
        original_docx_template = self.report.docx_template
        original_pptx_template = self.report.pptx_template
        foreign_client = ClientFactory()
        foreign_docx_template = ReportDocxTemplateFactory(client=foreign_client)
        foreign_pptx_template = ReportPptxTemplateFactory(client=foreign_client)
        denied_redirect = (
            reverse("reporting:report_detail", kwargs={"pk": self.report.pk})
            + "#generate"
        )

        try:
            self.report.docx_template = foreign_docx_template
            self.report.save()
            response = self.client_mgr.get(self.docx_uri)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, denied_redirect)

            self.report.docx_template = original_docx_template
            self.report.pptx_template = foreign_pptx_template
            self.report.save()
            response = self.client_mgr.get(self.pptx_uri)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, denied_redirect)

            self.report.docx_template = foreign_docx_template
            self.report.pptx_template = original_pptx_template
            self.report.save()
            response = self.client_mgr.get(self.all_uri)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, denied_redirect)
        finally:
            self.report.docx_template = original_docx_template
            self.report.pptx_template = original_pptx_template
            self.report.save()

    def test_generation_denies_template_for_wrong_document_type(self):
        original_docx_template = self.report.docx_template
        original_pptx_template = self.report.pptx_template
        wrong_docx_template = ReportPptxTemplateFactory()
        wrong_pptx_template = ReportDocxTemplateFactory()
        denied_redirect = (
            reverse("reporting:report_detail", kwargs={"pk": self.report.pk})
            + "#generate"
        )

        try:
            self.report.docx_template = wrong_docx_template
            self.report.save()
            response = self.client_mgr.get(self.docx_uri)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, denied_redirect)

            self.report.docx_template = original_docx_template
            self.report.pptx_template = wrong_pptx_template
            self.report.save()
            response = self.client_mgr.get(self.pptx_uri)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, denied_redirect)

            self.report.docx_template = wrong_docx_template
            self.report.pptx_template = original_pptx_template
            self.report.save()
            response = self.client_mgr.get(self.all_uri)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, denied_redirect)
        finally:
            self.report.docx_template = original_docx_template
            self.report.pptx_template = original_pptx_template
            self.report.save()

    def test_view_docx_with_missing_template(self):
        good_template = self.report.docx_template
        bad_template = ReportDocxTemplateFactory()
        self.report.docx_template = bad_template
        self.report.save()

        self.assertTrue(os.path.isfile(bad_template.document.path))
        os.remove(bad_template.document.path)
        self.assertFalse(os.path.isfile(bad_template.document.path))

        response = self.client_mgr.get(self.docx_uri)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(
            str(messages[0]),
            "Error: The word template could not be found on the server – try uploading it again. Occurred in the DOCX template",
        )

        self.report.docx_template = good_template
        self.report.save()


class ReportTemplateFilterTests(TestCase):
    """Collection of tests for custom Jinja2 filters for report templates."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.critical_sev = SeverityFactory(severity="Critical", weight=0)
        cls.high_sev = SeverityFactory(severity="High", weight=1)
        cls.med_sev = SeverityFactory(severity="Medium", weight=1)
        cls.network_type = FindingTypeFactory(finding_type="Network")
        cls.web_type = FindingTypeFactory(finding_type="Web")
        cls.mobile_type = FindingTypeFactory(finding_type="Mobile")

        ReportFindingLinkFactory.create_batch(
            2,
            report=cls.report,
            severity=cls.critical_sev,
            finding_type=cls.network_type,
            tags=["xss", "T1659"],
        )
        ReportFindingLinkFactory.create_batch(
            2,
            report=cls.report,
            severity=cls.high_sev,
            finding_type=cls.web_type,
        )
        ReportFindingLinkFactory.create_batch(
            2,
            report=cls.report,
            severity=cls.med_sev,
            finding_type=cls.mobile_type,
        )

        ProjectTargetFactory.create_batch(5, compromised=True, project=cls.project)
        ProjectTargetFactory.create_batch(5, compromised=False, project=cls.project)

        cls.serializer = ReportDataSerializer(
            cls.report,
            exclude=[
                "id",
            ],
        )
        report_json = JSONRenderer().render(cls.serializer.data)
        cls.report_json = json.loads(report_json)
        cls.findings = cls.report_json["findings"]
        cls.targets = cls.report_json["targets"]

        cls.test_date_string = "d M Y"
        cls.new_date_string = "M d, Y"
        cls.test_date = datetime(2022, 3, 28)

    def setUp(self):
        pass

    def test_format_datetime(self):
        test_date = dateformat(self.test_date, self.test_date_string)
        new_date = format_datetime(test_date, self.new_date_string)
        self.assertEqual(new_date, "Mar 28, 2022")

    def test_format_datetime_with_invalid_string(self):
        test_date = "Not a Date"
        with self.assertRaises(InvalidFilterValue):
            format_datetime(test_date, self.new_date_string)

    def test_add_days(self):
        test_date = dateformat(self.test_date, self.test_date_string)
        future_date = "11 Apr 2022"
        past_date = "21 Mar 2022"

        new_date = add_days(test_date, 10)
        self.assertEqual(new_date, future_date)

        new_date = add_days(test_date, -5)
        self.assertEqual(new_date, past_date)

    def test_to_datetime(self):
        test_date = dateformat(self.test_date, self.test_date_string)

        parsed_date = to_datetime(test_date, "%d %b %Y")
        self.assertEqual(parsed_date, self.test_date)

    def test_to_datetime_uses_default_format_when_omitted(self):
        test_date = dateformat(self.test_date, self.test_date_string)

        parsed_date = to_datetime(test_date)
        self.assertEqual(parsed_date, self.test_date)

    def test_to_datetime_uses_default_format_when_empty(self):
        test_date = dateformat(self.test_date, self.test_date_string)

        parsed_date = to_datetime(test_date, "")
        self.assertEqual(parsed_date, self.test_date)

    def test_to_datetime_uses_default_format_when_none(self):
        test_date = dateformat(self.test_date, self.test_date_string)

        parsed_date = to_datetime(test_date, None)
        self.assertEqual(parsed_date, self.test_date)

    @override_settings(DATE_INPUT_FORMATS=["%m/%d/%Y"])
    def test_to_datetime_uses_overridden_default_numeric_input_format(self):
        test_date = dateformat(self.test_date, "m/d/Y")

        parsed_date = to_datetime(test_date)
        self.assertEqual(parsed_date, self.test_date)

    @override_settings(DATE_INPUT_FORMATS=["%d %B %Y"])
    def test_to_datetime_uses_overridden_default_month_name_input_format(self):
        test_date = dateformat(self.test_date, "d F Y")

        parsed_date = to_datetime(test_date)
        self.assertEqual(parsed_date, self.test_date)

    def test_to_datetime_with_invalid_string(self):
        test_date = "Not a Date"
        with self.assertRaises(InvalidFilterValue):
            to_datetime(test_date, "%d %b %Y")

    def test_business_days_datetime(self):
        end_date = self.test_date + timedelta(days=13)

        # Monday to Monday
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2025, 12, 12)

        business_days_count = business_days(start_date, end_date)
        self.assertEqual(business_days_count, 10)

    def test_business_days_string(self):
        start_date = dateformat(self.test_date, self.test_date_string)
        end_date = dateformat(
            self.test_date + timedelta(days=13), self.test_date_string
        )

        business_days_count = business_days(start_date, end_date)
        self.assertEqual(business_days_count, 10)

    def test_business_days_with_invalid_datetime(self):
        test_date = "Not a Date"
        test_date2 = "Also Not a Date"
        with self.assertRaises(InvalidFilterValue):
            business_days(test_date, test_date2)

    def test_add_days_with_invalid_string(self):
        test_date = "Not a Date"
        with self.assertRaises(InvalidFilterValue):
            add_days(test_date, 10)

    def test_compromised(self):
        filtered_list = compromised(self.targets)
        self.assertEqual(len(filtered_list), 5)

    def test_compromised_with_invalid_dict(self):
        targets = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            compromised(targets)

    def test_filter_type(self):
        filtered_list = filter_type(self.findings, ["Network", "Web"])
        self.assertEqual(len(filtered_list), 4)

    def test_filter_type_with_invalid_dict(self):
        findings = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            filter_type(findings, ["Network", "Web"])

    def test_filter_type_with_invalid_allowlist(self):
        with self.assertRaises(InvalidFilterValue):
            filter_type(self.findings, "Network")

    def test_filter_severity(self):
        filtered_list = filter_severity(self.findings, ["Critical", "High"])
        self.assertEqual(len(filtered_list), 4)

    def test_filter_severity_with_invalid_dict(self):
        findings = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            filter_severity(findings, ["Critical", "High"])

    def test_filter_severity_with_invalid_allowlist(self):
        with self.assertRaises(InvalidFilterValue):
            filter_severity(self.findings, "Critical")

    def test_strip_html(self):
        test_string = "<p>This is a test<br />with a newline</p>"
        result = strip_html(test_string)
        self.assertEqual(result, "This is a test\nwith a newline")

    def test_get_item(self):
        test_list = ["a", "b", "c"]
        result = get_item(test_list, 1)
        self.assertEqual(result, "b")

    def test_regex_search(self):
        test_string = "This is a test string. It contains the word 'test'."
        result = regex_search(test_string, r"^(.*?)\.")
        self.assertEqual(result, "This is a test string.")

    def test_filter_tags(self):
        filtered_list = filter_tags(self.findings, ["xss", "T1659"])
        self.assertEqual(len(filtered_list), 2)

    def test_filter_tags_with_invalid_dict(self):
        findings = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            filter_tags(findings, ["xss", "T1659"])

    def test_replace_blanks(self):
        example = [
            {"example": "This is a test"},
            {"example": None},
            {"example": "This is another test"},
        ]
        res = replace_blanks(example, "BLANK")
        self.assertEqual(
            res,
            [
                {"example": "This is a test"},
                {"example": "BLANK"},
                {"example": "This is another test"},
            ],
        )
        with self.assertRaises(InvalidFilterValue):
            replace_blanks("Not a list", "BLANK")

    def test_filter_bhe_findings_by_domain(self):
        findings = [
            {"environment_id": "example.com"},
            {"environment_id": "test.com"},
            {"environment_id": "example.com"},
        ]
        filtered = filter_bhe_findings_by_domain(findings, "example.com")
        self.assertEqual(len(filtered), 2)

        findings_with_missing_domain = [
            {"environment_id": None},
            {"environment_id": "example.com"},
            {},
        ]
        filtered = filter_bhe_findings_by_domain(findings_with_missing_domain, None)
        self.assertEqual(filtered, [])
        filtered = filter_bhe_findings_by_domain(
            findings_with_missing_domain, "example.com"
        )
        self.assertEqual(filtered, [{"environment_id": "example.com"}])

        with self.assertRaises(InvalidFilterValue):
            filter_bhe_findings_by_domain("Not a list", "example.com")

    def test_translate_domain_sid(self):
        domains = [
            {"name": "MISSINGSID"},
            {
                "name": "GHOSTWRITER",
                "domain_sid": "S-1-5-21-1234567890-123456789-1234567890-1001",
            },
            {
                "name": "EXAMPLE",
                "domain_sid": "S-1-5-21-0987654321-987654321-9876543210",
            },
        ]
        translated = translate_domain_sid(
            "S-1-5-21-1234567890-123456789-1234567890-1001", domains
        )
        self.assertEqual(translated, "GHOSTWRITER")

        with self.assertRaises(InvalidFilterValue):
            translate_domain_sid(
                "S-1-5-21-0000000000-000000000-0000000000-1001", "Not a list"
            )


class LocalFindingNoteUpdateTests(TestCase):
    """Collection of tests for :view:`reporting.LocalFindingNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.LocalFindingNote = LocalFindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = LocalFindingNoteFactory(operator=cls.user)
        cls.uri = reverse(
            "reporting:local_finding_note_edit", kwargs={"pk": cls.note.pk}
        )
        cls.other_user_note = LocalFindingNoteFactory()
        cls.other_user_uri = reverse(
            "reporting:local_finding_note_edit", kwargs={"pk": cls.other_user_note.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class LocalFindingNoteDeleteTests(TestCase):
    """Collection of tests for :view:`reporting.LocalFindingNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.LocalFindingNote = LocalFindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        self.LocalFindingNote.objects.all().delete()
        note = LocalFindingNoteFactory(operator=self.user)
        uri = reverse(
            "reporting:ajax_delete_local_finding_note", kwargs={"pk": note.pk}
        )

        self.assertEqual(len(self.LocalFindingNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.LocalFindingNote.objects.all()), 0)

    def test_view_permissions(self):
        note = LocalFindingNoteFactory()
        uri = reverse(
            "reporting:ajax_delete_local_finding_note", kwargs={"pk": note.pk}
        )

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = LocalFindingNoteFactory()
        uri = reverse(
            "reporting:ajax_delete_local_finding_note", kwargs={"pk": note.pk}
        )

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)


class FindingNoteUpdateTests(TestCase):
    """Collection of tests for :view:`reporting.FindingNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.FindingNote = FindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = FindingNoteFactory(operator=cls.user)
        cls.uri = reverse("reporting:finding_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = FindingNoteFactory()
        cls.other_user_uri = reverse(
            "reporting:finding_note_edit", kwargs={"pk": cls.other_user_note.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class FindingNoteDeleteTests(TestCase):
    """Collection of tests for :view:`reporting.FindingNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.FindingNote = FindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        self.FindingNote.objects.all().delete()
        note = FindingNoteFactory(operator=self.user)
        uri = reverse("reporting:ajax_delete_finding_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.FindingNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.FindingNote.objects.all()), 0)

    def test_view_permissions(self):
        note = FindingNoteFactory()
        uri = reverse("reporting:ajax_delete_finding_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = FindingNoteFactory()
        uri = reverse("reporting:ajax_delete_finding_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)


class EvidenceDownloadTests(TestCase):
    """Collection of tests for :view:`reporting.EvidenceDownload`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.evidence_file = EvidenceFactory()
        cls.deleted_evidence_file = EvidenceFactory()
        cls.uri = reverse(
            "reporting:evidence_download", kwargs={"pk": cls.evidence_file.pk}
        )
        cls.deleted_uri = reverse(
            "reporting:evidence_download", kwargs={"pk": cls.deleted_evidence_file.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.client_mgr = Client()
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        """Test default behavior downloads file (as_attachment=True)."""
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            f'attachment; filename="{self.evidence_file.filename}"',
        )
        # Verify security header is present
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

    def test_view_inline_with_view_parameter(self):
        """Test inline viewing with ?view=true parameter."""
        response = self.client_mgr.get(f"{self.uri}?view=true")
        self.assertEqual(response.status_code, 200)
        # Should NOT have attachment disposition for inline viewing
        content_disposition = response.get("Content-Disposition")
        if content_disposition:
            self.assertNotIn("attachment", content_disposition)
        # Verify security headers
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("Content-Security-Policy", response)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(
            operator=self.user, project=self.evidence_file.report.project
        )
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        response = self.client_mgr.get(self.deleted_uri)
        self.assertEqual(response.status_code, 200)

        if os.path.exists(self.deleted_evidence_file.document.path):
            os.remove(self.deleted_evidence_file.document.path)

        response = self.client_mgr.get(self.deleted_uri)
        self.assertEqual(response.status_code, 404)


class EvidencePreviewTests(TestCase):
    """Collection of tests for :view:`reporting.EvidencePreview`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.evidence_file = EvidenceFactory()
        cls.deleted_evidence_file = EvidenceFactory()
        cls.unknown_evidence = EvidenceFactory(unknown=True)
        cls.uri = reverse(
            "reporting:evidence_preview", kwargs={"pk": cls.evidence_file.pk}
        )
        cls.unknown_uri = reverse(
            "reporting:evidence_preview", kwargs={"pk": cls.unknown_evidence.pk}
        )
        cls.deleted_uri = reverse(
            "reporting:evidence_preview", kwargs={"pk": cls.deleted_evidence_file.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.client_mgr = Client()
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(
            operator=self.user, project=self.evidence_file.report.project
        )
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        response = self.client_mgr.get(self.deleted_uri)
        self.assertEqual(response.status_code, 200)

        if os.path.exists(self.deleted_evidence_file.document.path):
            os.remove(self.deleted_evidence_file.document.path)

        response = self.client_mgr.get(self.deleted_uri)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML("<p>FILE NOT FOUND</p>", response.content.decode())

        response = self.client_mgr.get(self.unknown_uri)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            "<p>Evidence file type cannot be displayed.</p>", response.content.decode()
        )


# Tests related to :model:`reporting.Observation`


class ObservationListViewTests(TestCase):
    """Collection of tests for :view:`reporting.ObservationList`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.observation = ObservationFactory(title="Visible Observation")
        cls.observation.tags.add("visible-observation-tag")
        cls.uri = reverse("reporting:observations")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/observation_list.html")

    def test_tags_are_scoped_to_observations(self):
        hidden_report = ReportFactory(title="Hidden Tagged Report")
        hidden_report.tags.add("hidden-report-tag")
        hidden_project = ProjectFactory()
        hidden_project.tags.add("hidden-project-tag")
        hidden_finding = FindingFactory(title="Hidden Tagged Finding")
        hidden_finding.tags.add("hidden-finding-tag")

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-observation-tag", tag_names)
        self.assertNotIn("hidden-report-tag", tag_names)
        self.assertNotIn("hidden-project-tag", tag_names)
        self.assertNotIn("hidden-finding-tag", tag_names)

    def test_tags_are_scoped_to_filtered_observation_queryset(self):
        other_observation = ObservationFactory(title="Other Observation")
        other_observation.tags.add("other-observation-tag")

        response = self.client_auth.get(self.uri + "?observation=Visible")
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-observation-tag", tag_names)
        self.assertNotIn("other-observation-tag", tag_names)


class ObservationCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ObservationCreate`."""


    @classmethod
    def setUpTestData(cls):
        cls.observation = ObservationFactory()
        cls.Observation = ObservationFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("reporting:observation_create")
        cls.failure_redirect_uri = reverse("reporting:observations")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + self.uri)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        self.user.enable_observation_create = True
        self.user.save()
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 302)


class ObservationUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ObservationUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.observation = ObservationFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:observation_update", kwargs={"pk": cls.observation.pk}
        )
        cls.failure_redirect_uri = reverse("reporting:observations")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        self.user.enable_observation_edit = True
        self.user.save()
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/observation_update.html")


class ObservationDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.ObservationDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.observation = ObservationFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:observation_delete", kwargs={"pk": cls.observation.pk}
        )
        cls.failure_redirect_uri = reverse(
            "reporting:observation_detail", kwargs={"pk": cls.observation.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.failure_redirect_uri)

        self.user.enable_observation_delete = True
        self.user.save()
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:observations"),
        )
        self.assertEqual(
            response.context["object_type"],
            "observation",
        )
        self.assertEqual(
            response.context["object_to_be_deleted"], self.observation.title
        )


class AssignObservationViewTests(TestCase):
    """Collection of tests for :view:`reporting.AssignObservation`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.observation = ObservationFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse(
            "reporting:ajax_assign_observation", kwargs={"pk": cls.observation.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_response_with_session_vars_with_permissions(self):
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = self.report.id
        self.session["active_report"]["title"] = self.report.title
        self.session.save()

        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.id, "title": self.report.title},
        )

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(operator=self.user, project=self.report.project)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_response_with_report_id(self):
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session.save()

        response = self.client_mgr.post(self.uri, data={"report": self.report.id})
        self.assertEqual(response.status_code, 200)

    def test_view_response_with_bad_session_vars(self):
        self.session = self.client_mgr.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = 999
        self.session["active_report"]["title"] = self.report.title
        self.session.save()

        self.assertEqual(
            self.session["active_report"],
            {"id": 999, "title": self.report.title},
        )

        response = self.client_mgr.post(self.uri)
        message = "Please select a report to edit in the sidebar or go to a report's dashboard to assign an observation."
        data = {"result": "error", "message": message}

        self.assertJSONEqual(force_str(response.content), data)

    def test_view_response_without_session_vars(self):
        self.session = self.client_mgr.session
        self.session["active_report"] = None
        self.session.save()

        self.assertEqual(self.session["active_report"], None)

        response = self.client_mgr.post(self.uri)
        message = "Please select a report to edit in the sidebar or go to a report's dashboard to assign an observation."
        data = {"result": "error", "message": message}

        self.assertJSONEqual(force_str(response.content), data)

    def test_observation_assigned_to_requesting_user(self):
        response = self.client_mgr.post(self.uri, data={"report": self.report.id})
        self.assertEqual(response.status_code, 200)
        rol = ReportObservationLink.objects.filter(report=self.report).last()
        self.assertIsNotNone(rol)
        self.assertEqual(rol.assigned_to, self.mgr_user)


class AssignBlankObservationTests(TestCase):
    """Collection of tests for :view:`reporting.AssignBlankObservation`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse(
            "reporting:assign_blank_observation", kwargs={"pk": cls.report.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + self.uri)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

        ProjectAssignmentFactory(operator=self.user, project=self.report.project)
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_blank_observation_assigned_to_requesting_user(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        rol = ReportObservationLink.objects.filter(report=self.report).last()
        self.assertIsNotNone(rol)
        self.assertEqual(rol.assigned_to, self.mgr_user)


class ReportObservationStatusUpdateTests(TestCase):
    """Collection of tests for :view:`reporting.ReportObservationStatusUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.observation = ReportObservationLinkFactory(report=cls.report)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        uri = reverse(
            "reporting:ajax_set_observation_status",
            kwargs={"pk": self.observation.pk, "status": "edit"},
        )
        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_permissions(self):
        uri = reverse(
            "reporting:ajax_set_observation_status",
            kwargs={"pk": self.observation.pk, "status": "edit"},
        )
        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 403)

    def test_set_observation_complete(self):
        uri = reverse(
            "reporting:ajax_set_observation_status",
            kwargs={"pk": self.observation.pk, "status": "complete"},
        )
        response = self.client_mgr.post(uri)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"], "success")
        self.assertEqual(data["status"], "Ready")
        self.assertEqual(data["classes"], "healthy")
        self.observation.refresh_from_db()
        self.assertTrue(self.observation.complete)

    def test_set_observation_needs_editing(self):
        uri = reverse(
            "reporting:ajax_set_observation_status",
            kwargs={"pk": self.observation.pk, "status": "edit"},
        )
        response = self.client_mgr.post(uri)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"], "success")
        self.assertEqual(data["status"], "Needs Editing")
        self.assertEqual(data["classes"], "burned")
        self.observation.refresh_from_db()
        self.assertFalse(self.observation.complete)

    def test_set_observation_invalid_status(self):
        uri = reverse(
            "reporting:ajax_set_observation_status",
            kwargs={"pk": self.observation.pk, "status": "bogus"},
        )
        response = self.client_mgr.post(uri)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"], "error")


class ReportObservationLinkAssignTests(TestCase):
    """Collection of tests for :view:`reporting.ReportObservationLinkAssign`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.operator = UserFactory(password=PASSWORD)
        cls.observation = ReportObservationLinkFactory(
            report=cls.report, assigned_to=cls.mgr_user
        )
        ProjectAssignmentFactory(operator=cls.operator, project=cls.report.project)
        ProjectAssignmentFactory(operator=cls.mgr_user, project=cls.report.project)
        cls.uri = reverse(
            "reporting:local_observation_assign", kwargs={"pk": cls.observation.pk}
        )
        cls.success_url = (
            reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})
            + "#observations"
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=" + self.uri)

    def test_view_requires_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home:dashboard"))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_project_member_can_access(self):
        client_operator = Client()
        self.assertTrue(
            client_operator.login(username=self.operator.username, password=PASSWORD)
        )
        response = client_operator.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reporting/report_observation_link_assign.html"
        )

    def test_form_only_shows_project_members(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        queryset = form.fields["assigned_to"].queryset
        self.assertIn(self.operator, queryset)
        self.assertIn(self.mgr_user, queryset)
        self.assertNotIn(self.user, queryset)

    def test_reassign_observation(self):
        response = self.client_mgr.post(
            self.uri, data={"assigned_to": self.operator.pk}
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.success_url)
        updated = ReportObservationLink.objects.get(pk=self.observation.pk)
        self.assertEqual(updated.assigned_to, self.operator)

    def test_no_change_shows_info_message(self):
        response = self.client_mgr.post(
            self.uri, data={"assigned_to": self.mgr_user.pk}
        )
        self.assertEqual(response.status_code, 302)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already assigned" in str(m) for m in msgs))

    def test_unassign_observation(self):
        response = self.client_mgr.post(self.uri, data={"assigned_to": ""})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.success_url)
        updated = ReportObservationLink.objects.get(pk=self.observation.pk)
        self.assertIsNone(updated.assigned_to)
