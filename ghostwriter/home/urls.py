"""This contains all of the URL mappings used by the Home application."""

# Django Imports
from django.urls import path

# Ghostwriter Libraries
import ghostwriter.home.views as views

app_name = "home"

# URLs for the basic views
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("management/", views.Management.as_view(), name="management"),
    path("profile/avatar", views.upload_avatar, name="upload_avatar"),
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
]
