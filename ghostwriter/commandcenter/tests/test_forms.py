# Standard Libraries
import logging
from django.forms import ValidationError

# Django Imports
from django.forms.models import inlineformset_factory
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.commandcenter.admin import ExtraFieldSpecInlineFormSet
from ghostwriter.commandcenter.models import ExtraFieldModel, ExtraFieldSpec
from ghostwriter.commandcenter.forms import ExtraFieldsField, ExtraFieldsWidget, ReportConfigurationForm
from ghostwriter.factories import (
    ExtraFieldSpecFactory,
    ReportConfigurationFactory,
    ReportDocxTemplateFactory,
    ReportPptxTemplateFactory,
)

logging.disable(logging.CRITICAL)


def instantiate_formset(formset_class, data, instance=None, initial=None):
    prefix = formset_class.get_default_prefix()
    formset_data = {}
    for i, form_data in enumerate(data):
        for name, value in form_data.items():
            if name.endswith("_id"):
                name = name.replace("_id", "")
            formset_data["{}-{}-{}".format(prefix, i, name)] = value
    formset_data["{}-TOTAL_FORMS".format(prefix)] = len(data)
    formset_data["{}-INITIAL_FORMS".format(prefix)] = len(data)

    if instance:
        return formset_class(formset_data, instance=instance, initial=initial)
    else:
        return formset_class(formset_data, initial=initial)


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
        figure_caption_location=None,
        prefix_table=None,
        label_table=None,
        table_caption_location=None,
        report_filename=None,
        project_filename=None,
        default_docx_template_id=None,
        default_pptx_template_id=None,
        title_case_captions=None,
        title_case_exceptions=None,
        target_delivery_date=None,
        default_cvss_version=None,
        outline_tags=None,
        **kwargs,
    ):
        return ReportConfigurationForm(
            data={
                "enable_borders": enable_borders,
                "border_weight": border_weight,
                "border_color": border_color,
                "prefix_figure": prefix_figure,
                "label_figure": label_figure,
                "figure_caption_location": figure_caption_location,
                "prefix_table": prefix_table,
                "label_table": label_table,
                "table_caption_location": table_caption_location,
                "report_filename": report_filename,
                "project_filename": project_filename,
                "default_docx_template": default_docx_template_id,
                "default_pptx_template": default_pptx_template_id,
                "title_case_captions": title_case_captions,
                "title_case_exceptions": title_case_exceptions,
                "target_delivery_date": target_delivery_date,
                "default_cvss_version": default_cvss_version,
                "outline_tags": outline_tags,
            },
        )

    def test_valid_data(self):
        form = self.form_data(**self.config.__dict__)
        self.assertTrue(form.is_valid())

    def test_clean_default_docx_template(self):
        config = self.config.__dict__.copy()
        form = self.form_data(**config)
        if not form.is_valid():
            self.fail(f"Form was not valid, errors: {form.errors!r}")

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

    def test_clean_outline_tags_normalizes_and_deduplicates_rules(self):
        config = self.config.__dict__.copy()
        config["outline_tags"] = " report , EVIDENCE, cred* , att&ck: , cred* , ATT&CK:* ,, "

        form = self.form_data(**config)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["outline_tags"], "report,evidence,cred*,att&ck:*")

    def test_clean_outline_tags_rejects_malformed_rules(self):
        config = self.config.__dict__.copy()
        config["outline_tags"] = "report,foo::,cred**"

        form = self.form_data(**config)

        self.assertFalse(form.is_valid())
        self.assertIn("outline_tags", form.errors)


class ExtraFieldFormTest(TestCase):
    """Collection of tests for :form:`commandcenter.ExtraFieldSpec`"""

    @classmethod
    def setUpTestData(cls):
        cls.model = ExtraFieldModel.objects.create(
            model_internal_name="test.TestModel",
            model_display_name="Test Model",
        )
        ExtraFieldSpec.objects.create(
            target_model=cls.model,
            internal_name="test_field_single_line",
            display_name="Test Field 1",
            type="single_line_text",
        )
        ExtraFieldSpec.objects.create(
            target_model=cls.model,
            internal_name="test_field_rich",
            display_name="Test Field 2",
            type="rich_text",
        )
        ExtraFieldSpec.objects.create(
            target_model=cls.model,
            internal_name="test_field_integer",
            display_name="Test Field 3",
            type="integer",
        )

    def test_widget_has_fields(self):
        widget = ExtraFieldsWidget("test.TestModel")
        context = widget.get_context("testform", None, {})
        subwidgets = context["widget"]["subwidgets"]
        self.assertEqual(len(subwidgets), 3)
        self.assertEqual(subwidgets[0]["label"], "Test Field 1")
        self.assertEqual(subwidgets[0]["widget"]["name"], "testform_test_field_single_line")
        self.assertEqual(subwidgets[0]["widget"]["type"], "text")
        self.assertEqual(subwidgets[1]["label"], "Test Field 2")
        self.assertEqual(subwidgets[1]["widget"]["name"], "testform_test_field_rich")
        self.assertEqual(subwidgets[2]["label"], "Test Field 3")
        self.assertEqual(subwidgets[2]["widget"]["name"], "testform_test_field_integer")
        self.assertEqual(subwidgets[2]["widget"]["type"], "number")

    def test_widget_orders_fields_by_position(self):
        rich = ExtraFieldSpec.objects.get(internal_name="test_field_rich")
        integer = ExtraFieldSpec.objects.get(internal_name="test_field_integer")
        single_line = ExtraFieldSpec.objects.get(internal_name="test_field_single_line")

        rich.position = 1
        rich.save()
        integer.position = 2
        integer.save()
        single_line.position = 3
        single_line.save()

        widget = ExtraFieldsWidget("test.TestModel")
        labels = [field["label"] for field in widget.get_context("testform", None, {})["widget"]["subwidgets"]]

        self.assertEqual(labels, ["Test Field 2", "Test Field 3", "Test Field 1"])

    def test_widget_values(self):
        widget = ExtraFieldsWidget("test.TestModel")
        input_data = {
            "testform_test_field_single_line": "Hello world!",
            "testform_test_field_rich": "<p>Formatted</p><p>Text</p>",
            "testform_test_field_integer": "123",
            "unrelated_field": "Should not be in the output!",
        }
        output_data = widget.value_from_datadict(input_data, [], "testform")
        self.assertDictEqual(
            output_data,
            {
                "test_field_single_line": "Hello world!",
                "test_field_rich": "<p>Formatted</p><p>Text</p>",
                "test_field_integer": "123",
            },
        )

    def test_field_clean(self):
        field = ExtraFieldsField("test.TestModel")
        input_data = {
            "test_field_single_line": "Hello world!",
            "test_field_rich": "<p>Formatted</p><p>Text</p>",
            "test_field_integer": "123",
        }
        output_data = field.clean(input_data)
        self.assertDictEqual(
            output_data,
            {
                "test_field_single_line": "Hello world!",
                "test_field_rich": "<p>Formatted</p><p>Text</p>",
                "test_field_integer": 123,
            },
        )

    def test_field_clean_errors(self):
        field = ExtraFieldsField("test.TestModel")
        input_data = {
            "test_field_single_line": "Hello world!",
            "test_field_rich": "<p>Formatted</p><p>Text</p>",
            "test_field_integer": "this isn't an integer!",
        }
        with self.assertRaises(ValidationError):
            field.clean(input_data)

    def test_field_clean_missing(self):
        field = ExtraFieldsField("test.TestModel")
        input_data = {}
        output_data = field.clean(input_data)
        self.assertDictEqual(
            output_data,
            {
                "test_field_single_line": "",
                "test_field_rich": "",
                "test_field_integer": None,
            },
        )

    def test_checkbox_true(self):
        ExtraFieldSpec.objects.create(
            target_model=self.model,
            internal_name="test_field_bool",
            display_name="Test Field 4",
            type="checkbox",
        )
        field = ExtraFieldsField("test.TestModel")
        field_data = field.widget.value_from_datadict(
            {
                "testform_test_field_single_line": "Hello world!",
                "testform_test_field_rich": "<p>Formatted</p><p>Text</p>",
                "testform_test_field_integer": "123",
                "testform_test_field_bool": "on",
                "unrelated_field": "Should not be in the output!",
            },
            [],
            "testform",
        )
        self.assertTrue(field_data["test_field_bool"])
        data = field.clean(field_data)
        self.assertTrue(data["test_field_bool"])

    def test_checkbox_false(self):
        ExtraFieldSpec.objects.create(
            target_model=self.model,
            internal_name="test_field_bool",
            display_name="Test Field 4",
            type="checkbox",
        )
        field = ExtraFieldsField("test.TestModel")
        field_data = field.widget.value_from_datadict(
            {
                "testform_test_field_single_line": "Hello world!",
                "testform_test_field_rich": "<p>Formatted</p><p>Text</p>",
                "testform_test_field_integer": "123",
                "unrelated_field": "Should not be in the output!",
            },
            [],
            "testform",
        )
        self.assertFalse(field_data["test_field_bool"])
        data = field.clean(field_data)
        self.assertFalse(data["test_field_bool"])


class ExtraFieldSpecInlineFormSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.model = ExtraFieldModel.objects.create(
            model_internal_name="test.AdminModel",
            model_display_name="Admin Test Model",
        )
        cls.field_1 = ExtraFieldSpecFactory(
            target_model=cls.model,
            internal_name="first_field",
            display_name="First Field",
            type="single_line_text",
            position=1,
        )
        cls.field_2 = ExtraFieldSpecFactory(
            target_model=cls.model,
            internal_name="second_field",
            display_name="Second Field",
            type="single_line_text",
            position=2,
        )

    def form_data(self, data):
        formset_class = inlineformset_factory(
            ExtraFieldModel,
            ExtraFieldSpec,
            formset=ExtraFieldSpecInlineFormSet,
            fields="__all__",
            exclude=["target_model"],
            extra=0,
            can_delete=True,
        )
        return instantiate_formset(formset_class, data=data, instance=self.model)

    def test_duplicate_positions_raise_validation_error(self):
        first = self.field_1.__dict__.copy()
        second = self.field_2.__dict__.copy()
        second["position"] = 1

        formset = self.form_data([first, second])

        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.errors[0]["position"].as_data()[0].code, "duplicate")
        self.assertEqual(formset.errors[1]["position"].as_data()[0].code, "duplicate")

    def test_deleted_form_is_ignored_for_duplicate_positions(self):
        first = self.field_1.__dict__.copy()
        second = self.field_2.__dict__.copy()
        second["position"] = 1
        second["DELETE"] = True

        formset = self.form_data([first, second])

        self.assertTrue(formset.is_valid())
