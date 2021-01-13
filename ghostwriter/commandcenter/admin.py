"""This contains customizations for displaying the CommandCenter application models in the admin panel."""

# Django & Other 3rd Party Libraries
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
    Route53Configuration,
)

admin.site.register(CloudServicesConfiguration, SingletonModelAdmin)
admin.site.register(CompanyInformation, SingletonModelAdmin)
admin.site.register(NamecheapConfiguration, SingletonModelAdmin)
admin.site.register(SlackConfiguration, SingletonModelAdmin)
admin.site.register(VirusTotalConfiguration, SingletonModelAdmin)
admin.site.register(Route53Configuration, SingletonModelAdmin)


class ReportConfigurationAdmin(SingletonModelAdmin):
    form = ReportConfigurationForm


admin.site.register(ReportConfiguration, ReportConfigurationAdmin)
