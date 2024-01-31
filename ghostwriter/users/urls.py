"""This contains all the URL mappings used by the Users application."""

# Django Imports
from django.urls import path

# Ghostwriter Libraries
from ghostwriter.users.views import (
    avatar_download,
    user_detail_view,
    user_redirect_view,
    user_update_view,
    userprofile_update_view,
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("<str:username>/", user_detail_view, name="user_detail"),
    path("<str:username>/update/", user_update_view, name="user_update"),
    path("<str:username>/update/avatar/", view=userprofile_update_view, name="userprofile_update"),
    path(
        "<str:slug>/avatar",
        avatar_download,
        name="avatar_download",
    ),
]
