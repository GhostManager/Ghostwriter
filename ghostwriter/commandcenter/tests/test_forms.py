# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.commandcenter.forms import ReportConfigurationForm
from ghostwriter.factories import (
    ReportConfigurationFactory,
    ReportDocxTemplateFactory,
    ReportPptxTemplateFactory,
)

logging.disable(logging.CRITICAL)


class ReportConfigurationFormTests(TestCase):
    """Collection of tests for :form:`commandcenter.ReportConfigurationForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.valid_docx_template = ReportDocxTemplateFactory()
        cls.valid_pptx_template = ReportPptxTemplateFactory()

        cls.invalid_docx_template = ReportDocxTemplateFactory()
        cls.invalid_docx_template.lint_result = {"result": "failed", "warnings": [], "errors": []}
        cls.invalid_docx_template.save()

        cls.invalid_pptx_template = ReportPptxTemplateFactory()
        cls.invalid_pptx_template.lint_result = {"result": "failed", "warnings": [], "errors": []}
        cls.invalid_pptx_template.save()

        cls.config = ReportConfigurationFactory(
            default_docx_template_id=cls.valid_docx_template.pk, default_pptx_template_id=cls.valid_pptx_template.pk
        )

    def setUp(self):
        pass

    def form_data(
        self,
        enable_borders=None,
        border_weight=None,
        border_color=None,
        prefix_figure=None,
        label_figure=None,
        prefix_table=None,
        label_table=None,
        report_filename=None,
        default_docx_template_id=None,
        default_pptx_template_id=None,
        **kwargs,
    ):
        return ReportConfigurationForm(
            data={
                "enable_borders": enable_borders,
                "border_weight": border_weight,
                "border_color": border_color,
                "prefix_figure": prefix_figure,
                "label_figure": label_figure,
                "prefix_table": prefix_table,
                "label_table": label_table,
                "report_filename": report_filename,
                "default_docx_template": default_docx_template_id,
                "default_pptx_template": default_pptx_template_id,
            },
        )

    def test_valid_data(self):
        form = self.form_data(**self.config.__dict__)
        self.assertTrue(form.is_valid())

    def test_clean_default_docx_template(self):
        config = self.config.__dict__.copy()
        form = self.form_data(**config)
        self.assertTrue(form.is_valid())

        # Switch config to the invalid template
        config["default_docx_template_id"] = self.invalid_docx_template.pk

        form = self.form_data(**config)
        errors = form.errors["default_docx_template"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")

    def test_clean_default_pptx_template(self):
        config = self.config.__dict__.copy()
        form = self.form_data(**config)
        self.assertTrue(form.is_valid())

        # Switch config to the invalid template
        config["default_pptx_template_id"] = self.invalid_pptx_template.pk

        form = self.form_data(**config)
        errors = form.errors["default_pptx_template"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")
