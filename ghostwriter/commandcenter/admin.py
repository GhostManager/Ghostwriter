"""This contains customizations for displaying the CommandCenter application models in the admin panel."""

# Django Imports
from django.contrib import admin

# Ghostwriter Libraries
from ghostwriter.singleton.admin import SingletonModelAdmin

from .forms import ReportConfigurationForm
from .models import (
    CloudServicesConfiguration,
    CompanyInformation,
    NamecheapConfiguration,
    ReportConfiguration,
    SlackConfiguration,
    VirusTotalConfiguration,
)

admin.site.register(CloudServicesConfiguration, SingletonModelAdmin)
admin.site.register(CompanyInformation, SingletonModelAdmin)
admin.site.register(NamecheapConfiguration, SingletonModelAdmin)
admin.site.register(SlackConfiguration, SingletonModelAdmin)
admin.site.register(VirusTotalConfiguration, SingletonModelAdmin)


class ReportConfigurationAdmin(SingletonModelAdmin):
    form = ReportConfigurationForm


admin.site.register(ReportConfiguration, ReportConfigurationAdmin)
