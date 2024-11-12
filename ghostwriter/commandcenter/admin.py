"""This contains customizations for displaying the CommandCenter application models in the admin panel."""

# Django Imports
from django.contrib import admin
from django import forms

# Ghostwriter Libraries
from ghostwriter.commandcenter.forms import ReportConfigurationForm
from ghostwriter.commandcenter.models import (
    CloudServicesConfiguration,
    CompanyInformation,
    ExtraFieldModel,
    ExtraFieldSpec,
    GeneralConfiguration,
    NamecheapConfiguration,
    ReportConfiguration,
    SlackConfiguration,
    VirusTotalConfiguration,
    EXTRA_FIELD_TYPES,
)
from ghostwriter.singleton.admin import SingletonModelAdmin

admin.site.register(CloudServicesConfiguration, SingletonModelAdmin)
admin.site.register(CompanyInformation, SingletonModelAdmin)
admin.site.register(NamecheapConfiguration, SingletonModelAdmin)
admin.site.register(SlackConfiguration, SingletonModelAdmin)
admin.site.register(VirusTotalConfiguration, SingletonModelAdmin)
admin.site.register(GeneralConfiguration, SingletonModelAdmin)


class ReportConfigurationAdmin(SingletonModelAdmin):
    form = ReportConfigurationForm
    fieldsets = (
        (
            "Borders",
            {
                "fields": (
                    "enable_borders",
                    "border_weight",
                    "border_color",
                )
            },
        ),
        (
            "Captions",
            {
                "fields": (
                    "title_case_captions",
                    "title_case_exceptions",
                )
            },
        ),
        (
            "Figures",
            {
                "fields": (
                    "prefix_figure",
                    "label_figure",
                    "figure_caption_location",
                )
            },
        ),
        (
            "Tables",
            {
                "fields": (
                    "prefix_table",
                    "label_table",
                    "table_caption_location",
                )
            },
        ),
        (
            "Report Generation",
            {
                "fields": (
                    "report_filename",
                    "project_filename",
                    "target_delivery_date",
                    "default_docx_template",
                    "default_pptx_template",
                )
            },
        ),
    )


admin.site.register(ReportConfiguration, ReportConfigurationAdmin)


class ExtraFieldSpecForm(forms.ModelForm):
    internal_name = forms.RegexField(
        r"^[_a-zA-Z][_a-zA-Z0-9]*$",
        max_length=255,
        help_text="Name used in report templates and storage (no spaces)",
    )

    user_default_value = forms.CharField(
        required=False,
        strip=True,
        help_text="Value used in newly created objects. Changing this will not change existing objects, and newly created fields will be set to blank on existing objects.",
    )

    description = forms.CharField(
        required=False, strip=True, help_text="Help text shown under the extra field in forms"
    )

    def clean_user_default_value(self):
        field_type = self.cleaned_data.get("type")
        default_value = self.cleaned_data.get("user_default_value")
        if field_type is None:
            return default_value
        try:
            EXTRA_FIELD_TYPES[field_type].from_str(default_value)
        except ValueError:
            raise forms.ValidationError(f"Invalid default value for a(n) {field_type} extra field")
        return default_value

    class Meta:
        model = ExtraFieldSpec
        exclude = ["target_model"]


class ExtraFieldSpecInline(admin.TabularInline):
    model = ExtraFieldSpec
    form = ExtraFieldSpecForm


class ExtraFieldModelAdmin(admin.ModelAdmin):
    fields = ["model_display_name"]
    readonly_fields = ["model_display_name"]
    inlines = [
        ExtraFieldSpecInline,
    ]
    change_form_template = "user_extra_fields/admin_change_form.html"

    # These objects correspond to our app's models, so they should be added/removed only via fixtures
    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


admin.site.register(ExtraFieldModel, ExtraFieldModelAdmin)
