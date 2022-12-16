"""This contains all the URL mappings used by the Home application."""

# Django Imports
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

# Ghostwriter Libraries
from ghostwriter.home import views

app_name = "home"

# URLs for the basic views
urlpatterns = [
    path("", views.Dashboard.as_view(), name="dashboard"),
    path("management/", views.Management.as_view(), name="management"),
]

# URLs for AJAX test functions
urlpatterns += [
    path(
        "ajax/management/test/aws",
        views.TestAWSConnection.as_view(),
        name="ajax_test_aws",
    ),
    path(
        "ajax/management/test/do",
        views.TestDOConnection.as_view(),
        name="ajax_test_do",
    ),
    path(
        "ajax/management/test/namecheap",
        views.TestNamecheapConnection.as_view(),
        name="ajax_test_namecheap",
    ),
    path(
        "ajax/management/test/slack",
        views.TestSlackConnection.as_view(),
        name="ajax_test_slack",
    ),
    path(
        "ajax/management/test/virustotal",
        views.TestVirusTotalConnection.as_view(),
        name="ajax_test_virustotal",
    ),
    path(
        "ajax/session/update",
        csrf_exempt(views.update_session),
        name="ajax_update_session",
    ),
]
