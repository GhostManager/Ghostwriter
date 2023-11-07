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
            "Figures",
            {
                "fields": (
                    "prefix_figure",
                    "label_figure",
                )
            },
        ),
        (
            "Tables",
            {
                "fields": (
                    "prefix_table",
                    "label_table",
                )
            },
        ),
        (
            "Report Generation",
            {
                "fields": (
                    "report_filename",
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

    # These objects correspond to our app's models, so they should be added/removed only via fixtures
    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


admin.site.register(ExtraFieldModel, ExtraFieldModelAdmin)
