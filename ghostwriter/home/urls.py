"""This contains all of the URL mappings used by the Home application."""

from django.urls import path

from ghostwriter.home.views import (
    dashboard,
    management,
    profile,
    send_slack_test_msg,
    upload_avatar,
)

app_name = "home"

# URLs for the basic views
urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("profile/", profile, name="profile"),
    path("management/", management, name="management"),
    path("management/test_slack", send_slack_test_msg, name="send_slack_test_msg"),
    path("profile/avatar", upload_avatar, name="upload_avatar"),
]
