"""This contains customizations for displaying the CommandCenter application models in the admin panel."""

# Django Imports
from django.contrib import admin

# Ghostwriter Libraries
from ghostwriter.commandcenter.forms import ReportConfigurationForm
from ghostwriter.commandcenter.models import (
    CloudServicesConfiguration,
    CompanyInformation,
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
