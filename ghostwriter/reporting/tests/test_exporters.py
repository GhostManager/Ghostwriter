"""Regression tests for report and project exporter initialization."""

# Standard Libraries
import json
from unittest.mock import Mock

# Django Imports
from django.test import SimpleTestCase, TestCase

# Ghostwriter Libraries
from ghostwriter.factories import ReportFactory
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.project.docx import ExportProjectDocx
from ghostwriter.modules.reportwriter.project.json import ExportProjectJson
from ghostwriter.modules.reportwriter.project.pptx import ExportProjectPptx
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.modules.reportwriter.report.json import ExportReportJson
from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx
from ghostwriter.modules.reportwriter.report.xlsx import ExportReportXlsx


class ExportBaseInitializationTests(SimpleTestCase):
    """Verify the base exporter never dispatches into subclass code during initialization."""

    def test_uses_explicit_object_serializer(self):
        class FalseySerializer:
            def __init__(self):
                self.mock = Mock(return_value={"serialized": True})

            def __bool__(self):
                return False

            def __call__(self, input_object):
                return self.mock(input_object)

        input_object = object()
        serializer = FalseySerializer()

        exporter = ExportBase(input_object, object_serializer=serializer)

        serializer.mock.assert_called_once_with(input_object)
        self.assertIs(exporter.input_object, input_object)
        self.assertEqual(exporter.data, {"serialized": True})

    def test_raw_data_bypasses_object_serializer(self):
        raw_data = {"raw": True}
        serializer = Mock(side_effect=AssertionError("raw data must not be serialized"))

        exporter = ExportBase(raw_data, is_raw=True, object_serializer=serializer)

        serializer.assert_not_called()
        self.assertIsNone(exporter.input_object)
        self.assertEqual(exporter.data, raw_data)
        self.assertIsNot(exporter.data, raw_data)

    def test_does_not_call_subclass_serialization_method(self):
        class ExportWithOverriddenSerializer(ExportBase):
            def serialize_object(self, input_object):
                raise AssertionError("subclass method called during initialization")

        input_object = {"safe": True}

        exporter = ExportWithOverriddenSerializer(input_object)

        self.assertIs(exporter.input_object, input_object)
        self.assertEqual(exporter.data, input_object)
        self.assertIsNot(exporter.data, input_object)

    def test_rejects_non_serializable_context_objects(self):
        with self.assertRaisesRegex(TypeError, "JSON-serializable"):
            ExportBase({"unsafe": object()}, is_raw=True)


class ConcreteExporterInitializationTests(TestCase):
    """Verify every concrete exporter receives the correct serialized input."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.project = cls.report.project

    def test_report_exporters_initialize_with_report_data(self):
        exporters = [
            ExportReportJson(self.report),
            ExportReportDocx(
                self.report,
                report_template=self.report.docx_template,
            ),
            ExportReportXlsx(self.report),
            ExportReportPptx(
                self.report,
                report_template=self.report.pptx_template,
            ),
        ]

        try:
            for exporter in exporters:
                with self.subTest(exporter=type(exporter).__name__):
                    self.assertIs(exporter.input_object, self.report)
                    self.assertEqual(exporter.data["title"], self.report.title)
                    self.assertEqual(
                        exporter.data["project"]["name"],
                        str(self.project),
                    )
        finally:
            exporters[2].workbook.close()

    def test_report_context_contains_only_exact_json_primitives(self):
        exporter = ExportReportJson(self.report)

        def assert_primitives(value):
            self.assertIn(type(value), {dict, list, str, int, float, bool, type(None)})
            if type(value) is dict:
                for key, child in value.items():
                    self.assertIs(type(key), str)
                    assert_primitives(child)
            elif type(value) is list:
                for child in value:
                    assert_primitives(child)

        assert_primitives(exporter.data)

    def test_report_filename_cannot_reach_serializer_queryset(self):
        exporter = ExportReportJson(self.report)
        filename_template = (
            "{% if severities.serializer %}unsafe{% else %}safe{% endif %}"
        )

        self.assertEqual(exporter.render_filename(filename_template), "safe.json")

    def test_project_exporters_initialize_with_project_data(self):
        exporters = [
            ExportProjectJson(self.project),
            ExportProjectDocx(
                self.project,
                report_template=self.report.docx_template,
            ),
            ExportProjectPptx(
                self.project,
                report_template=self.report.pptx_template,
            ),
        ]

        for exporter in exporters:
            with self.subTest(exporter=type(exporter).__name__):
                self.assertIs(exporter.input_object, self.project)
                self.assertEqual(
                    exporter.data["project"]["name"],
                    str(self.project),
                )
                self.assertEqual(
                    exporter.data["client"]["name"],
                    self.project.client.name,
                )

    def test_report_json_export_preserves_bloodhound_option(self):
        exporter = ExportReportJson(
            self.report,
            include_bloodhound=False,
        )

        self.assertNotIn("bloodhound", exporter.data)

        output = exporter.run()
        output.seek(0)
        self.assertNotIn("bloodhound", json.load(output))

    def test_report_and_project_raw_exports_bypass_model_serialization(self):
        raw_data = {"raw": True}

        report_exporter = ExportReportJson(raw_data, is_raw=True)
        project_exporter = ExportProjectJson(raw_data, is_raw=True)

        self.assertEqual(report_exporter.data, raw_data)
        self.assertEqual(project_exporter.data, raw_data)
        self.assertIsNot(report_exporter.data, raw_data)
        self.assertIsNot(project_exporter.data, raw_data)
