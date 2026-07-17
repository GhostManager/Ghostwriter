# Copy this to `local.d` to enable the django-debug-toolbar.
#
# Only the development setup (using the `local.yml` compose file) has
# django-debug-toolbar installed.

INSTALLED_APPS += ["debug_toolbar"]  # noqa F405
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa F405
