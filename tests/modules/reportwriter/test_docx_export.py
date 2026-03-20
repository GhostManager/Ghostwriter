from django.test import TestCase

from ghostwriter.factories import (
    CompanyInformationFactory,
    ReportConfigurationFactory,
    ReportFactory,
)
from ghostwriter.modules.reportwriter.base.html_rich_text import HtmlRichText
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx


class ExportReportDocxRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.report_config = ReportConfigurationFactory(
            enable_borders=True,
            border_color="123456",
            border_weight=9876,
            prefix_figure=" :: ",
            label_figure="Figure Label",
            figure_caption_location="top",
            prefix_table=" -- ",
            label_table="Table Label",
            table_caption_location="bottom",
            title_case_captions=False,
            title_case_exceptions="a,an,the",
        )
        CompanyInformationFactory(pk=1)
        cls.report = ReportFactory()

    def create_exporter(self):
        return ExportReportDocx(self.report, report_template=self.report.docx_template)

    def test_exporter_initializes_docx_caption_and_border_attributes(self):
        exporter = self.create_exporter()

        assert exporter.enable_borders is True
        assert exporter.border_color == "123456"
        assert exporter.border_weight == 9876
        assert exporter.prefix_figure == " :: "
        assert exporter.label_figure == "Figure Label"
        assert exporter.figure_caption_location == "top"
        assert exporter.prefix_table == " -- "
        assert exporter.label_table == "Table Label"
        assert exporter.table_caption_location == "bottom"
        assert exporter.title_case_captions is False
        assert exporter.title_case_exceptions == ["a", "an", "the"]

    def test_render_rich_text_docx_uses_restored_exporter_attributes(self):
        exporter = self.create_exporter()
        captured = {}

        class FakeSubdoc:
            def __str__(self):
                return "rendered subdoc"

        exporter.word_doc.new_subdoc = lambda: FakeSubdoc()

        def fake_run(html, **kwargs):
            captured["html"] = html
            captured["kwargs"] = kwargs

        rich_text = HtmlRichText("<p>Wireless summary</p>", location="the AI review rich text field (wireless_rt)")

        from ghostwriter.modules.reportwriter.base import docx as docx_module

        original_run = docx_module.HtmlToDocxWithEvidence.run
        docx_module.HtmlToDocxWithEvidence.run = fake_run
        try:
            rendered = exporter.render_rich_text_docx(rich_text)
            assert str(rendered) == "rendered subdoc"
        finally:
            docx_module.HtmlToDocxWithEvidence.run = original_run

        assert captured["html"] == "<p>Wireless summary</p>"
        assert captured["kwargs"]["figure_label"] == "Figure Label"
        assert captured["kwargs"]["figure_prefix"] == " :: "
        assert captured["kwargs"]["figure_caption_location"] == "top"
        assert captured["kwargs"]["table_label"] == "Table Label"
        assert captured["kwargs"]["table_prefix"] == " -- "
        assert captured["kwargs"]["table_caption_location"] == "bottom"
        assert captured["kwargs"]["title_case_captions"] is False
        assert captured["kwargs"]["title_case_exceptions"] == ["a", "an", "the"]
        assert captured["kwargs"]["border_color_width"] == ("123456", 9876)
        assert captured["kwargs"]["global_report_config"] == self.report_config
