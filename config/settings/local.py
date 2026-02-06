from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="Vso7i8BApwA6km4L50PFRvqcTtGZHLrC1pnKLCXqfTWifhjbGq4nTd6ZrDH2Iobe",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
hosts = env("DJANGO_ALLOWED_HOSTS", default="localhost 0.0.0.0 127.0.0.1 172.20.0.5 django host.docker.internal 127.0.0.1:8000")
ALLOWED_HOSTS = hosts.split(" ")

STATICFILES_DIRS += [
    # Populated by frontend docker container
    "/app/javascript/dist_frontend/"
]

# MFA SETTINGS
# Optional -- use for local development only
# https://docs.allauth.org/en/dev/mfa/webauthn.html
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = True

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = "localhost"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
if env("USE_DOCKER") == "yes":
    import socket
    try:
        _, _, ips = socket.gethostbyname_ex("nginx")
        INTERNAL_IPS += ips
    except socket.gaierror:
        # nginx may not be resolvable yet during startup
        pass

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
#INSTALLED_APPS += ["django_extensions"]  # noqa F405

# Your stuff...
# ------------------------------------------------------------------------------

# LOGGING.setdefault("loggers", {})["django.db.backends"] = {
#     "level": "DEBUG"
# }

# Include files in `local.d`. These are added in alphabetical order - using a numeric prefix
# like `10-subconfig.py` can be used to order inclusions

include_settings("./local.d/*.py")
