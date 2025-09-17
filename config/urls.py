"""This contains the base URL mappings used by Ghostwriter."""

# Django Imports
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views import defaults as default_views
from django.views.generic import RedirectView

# Ghostwriter Libraries
from ghostwriter.home.views import protected_serve
from ghostwriter.users.views import (
    account_change_password,
    account_reset_password_from_key,
    RecoveryCodesView,
)

# Ensure users go through the allauth workflow when logging into admin
admin.site.login = staff_member_required(admin.site.login, login_url="/accounts/login")
# Run the standard admin set-up
admin.autodiscover()

urlpatterns = [
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("ghostwriter.users.urls", namespace="users")),
    path("home/", include("ghostwriter.home.urls", namespace="home")),
    path(
        "accounts/password/change/",
        account_change_password,
        name="account_change_password",
    ),
    re_path(
        r"^accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        account_reset_password_from_key,
        name="account_reset_password_from_key",
    ),
    path('accounts/2fa/recovery-codes/', RecoveryCodesView.as_view(), name='mfa_view_recovery_codes'),
    path("accounts/", include("allauth.urls")),
    # path("accounts/", include("django.contrib.auth.urls")),
    path("rolodex/", include("ghostwriter.rolodex.urls", namespace="rolodex")),
    path("shepherd/", include("ghostwriter.shepherd.urls", namespace="shepherd")),
    path("reporting/", include("ghostwriter.reporting.urls", namespace="reporting")),
    path("", RedirectView.as_view(pattern_name="home:dashboard"), name="home"),
    path("oplog/", include("ghostwriter.oplog.urls", namespace="oplog")),
    re_path(
        r"^%s(?P<path>.*)$" % settings.MEDIA_URL[1:],
        protected_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
    path("api/", include("ghostwriter.api.urls", namespace="api")),
    path("status/", include("ghostwriter.status.urls", namespace="status")),
    # Add additional custom paths below this line...
    # Your stuff: custom urls includes go here
]

if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()

    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:

        import debug_toolbar  # noqa isort:skip

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
