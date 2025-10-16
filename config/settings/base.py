"""
Base settings to build other settings files upon.
"""
# Standard Libraries
from datetime import timedelta
from pathlib import Path

# Django Imports
from django.contrib.messages import constants as messages

# 3rd Party Libraries
import environ

__version__ = "6.0.5"
VERSION = __version__
RELEASE_DATE = "16 October 2025"

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
APPS_DIR = ROOT_DIR / "ghostwriter"

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone – Choices are:
#   http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
#   Not all of them may be available with every OS
#   In Windows, this must be set to your system time zone
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = False
# https://docs.djangoproject.com/en/4.0/ref/settings/#date-format
DATE_FORMAT = env(
    "DJANGO_DATE_FORMAT",
    default="d M Y",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(ROOT_DIR / "locale")]
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
origins = env("DJANGO_CSRF_TRUSTED_ORIGINS", default="")
if origins:
    CSRF_TRUSTED_ORIGINS = origins.split(" ")

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "channels",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "allauth",
    "allauth.account",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "allauth_2fa",
    "allauth.socialaccount",
    "rest_framework",
    "rest_framework_api_key",
    "django_q",
    "django_filters",
    "import_export",
    "tinymce",
    "django_bleach",
    "timezone_field",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    "health_check.contrib.migrations",
    "health_check.contrib.psutil",
    "health_check.contrib.redis",
    "taggit",
]

LOCAL_APPS = [
    "ghostwriter.users.apps.UsersConfig",
    "ghostwriter.home.apps.HomeConfig",
    "ghostwriter.rolodex.apps.RolodexConfig",
    "ghostwriter.shepherd.apps.ShepherdConfig",
    "ghostwriter.reporting.apps.ReportingConfig",
    "ghostwriter.oplog.apps.OplogConfig",
    "ghostwriter.commandcenter.apps.CommandCenterConfig",
    "ghostwriter.singleton.apps.SingletonConfig",
    "ghostwriter.api.apps.ApiConfig",
    "ghostwriter.status.apps.StatusConfig",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# CHANNELS & WEBSOCKETS
# ------------------------------------------------------------------------------
# https://channels.readthedocs.io/en/stable/installation.html
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "ghostwriter.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "home:dashboard"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "allauth_2fa.middleware.AllauthTwoFactorMiddleware",
    "ghostwriter.middleware.Require2FAMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR / "static"),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"
# Default location for report templates
TEMPLATE_LOC = str(APPS_DIR / "media" / "templates")

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "ghostwriter.context_processors.selected_settings",
            ],
        },
    }
]
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap4"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/3.2/ref/settings/#session-cookie-age
SESSION_COOKIE_AGE = env("DJANGO_SESSION_COOKIE_AGE", default=60 * 60 * 2)
# https://docs.djangoproject.com/en/3.2/ref/settings/#session-expire-at-browser-close
SESSION_EXPIRE_AT_BROWSER_CLOSE = env("DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE", default=True)
# https://docs.djangoproject.com/en/3.2/topics/http/sessions/#when-sessions-are-saved
SESSION_SAVE_EVERY_REQUEST = env("DJANGO_SESSION_SAVE_EVERY_REQUEST", default=True)
# https://docs.djangoproject.com/en/3.2/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = env("DJANGO_SESSION_COOKIE_SECURE", default=False)
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = False
# https://docs.djangoproject.com/en/3.2/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = env("DJANGO_CSRF_COOKIE_SECURE", default=False)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "SAMEORIGIN"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# https://docs.djangoproject.com/en/2.2/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = []
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", False)
SOCIAL_ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_SOCIAL_ACCOUNT_ALLOW_REGISTRATION", False)
SOCIAL_ACCOUNT_DOMAIN_ALLOWLIST = env("DJANGO_SOCIAL_ACCOUNT_DOMAIN_ALLOWLIST", default="")
SOCIALACCOUNT_LOGIN_ON_GET = env.bool("DJANGO_SOCIAL_ACCOUNT_LOGIN_ON_GET", False)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = env.bool("DJANGO_ACCOUNT_EMAIL_VERIFICATION", "mandatory")
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "ghostwriter.users.adapters.CustomOTPAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "ghostwriter.users.adapters.SocialAccountAdapter"
ACCOUNT_SIGNUP_FORM_CLASS = "ghostwriter.home.forms.SignupForm"
ACCOUNT_FORMS = {
    "login": "ghostwriter.users.forms.UserLoginForm",
    "signup": "ghostwriter.users.forms.UserSignupForm",
}
ALLAUTH_2FA_FORMS = {
    "authenticate": "ghostwriter.users.forms.User2FAAuthenticateForm",
    "setup": "ghostwriter.users.forms.User2FADeviceForm",
    "remove": "ghostwriter.users.forms.User2FADeviceRemoveForm",
}
ALLAUTH_2FA_ALWAYS_REVEAL_BACKUP_TOKENS = env("DJANGO_2FA_ALWAYS_REVEAL_BACKUP_TOKENS", default=False)
ALLAUTH_2FA_SETUP_SUCCESS_URL = "users:redirect"
ALLAUTH_2FA_REMOVE_SUCCESS_URL = "users:redirect"

# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/quickstart/#installation
INSTALLED_APPS += ["compressor"]
STATICFILES_FINDERS += ["compressor.finders.CompressorFinder"]

# DJANGO MESSAGES
# ------------------------------------------------------------------------------
MESSAGE_TAGS = {
    messages.INFO: "alert alert-info",
    messages.SUCCESS: "alert alert-success",
    messages.WARNING: "alert alert-warning",
    messages.ERROR: "alert alert-danger",
}

# DJANGO Q
# ------------------------------------------------------------------------------

# Settings to be aware of:

# save_limit: Limits the amount of successful tasks saved to Django. Set to 35
# for roughly one month of daily tasks and some domain check-ups.

# timeout: The number of seconds a worker is allowed to spend on a task before
# it’s terminated. Defaults to None, meaning it will never time out. Can be
# overridden for individual tasks. Not set globally here because DNS and
# health checks can take a long time and will be different for everyone.

Q_CLUSTER = {
    "name": env("DJANGO_QCLUSTER_NAME", default="soar"),
    "timeout": 43200,
    "retry": 43200,
    "recycle": 500,
    "save_limit": 35,
    "queue_limit": 500,
    "cpu_affinity": 1,
    "label": "Django Q",
    "redis": env("QCLUSTER_CONNECTION", default={"host": "redis", "port": 6379, "db": 0}),
}

# SETTINGS
# ------------------------------------------------------------------------------
# All settings are stored in singleton models in the CommandCenter app
# Settings can be cached to avoid repeated database queries

# The cache that should be used, e.g. 'default'
# Set to ``None`` to disable caching
# Ghostwriter does not use a cache by default
SOLO_CACHE = None
SOLO_CACHE_TIMEOUT = 60 * 5
SOLO_CACHE_PREFIX = "solo"

# BLEACH
# ------------------------------------------------------------------------------
# Which HTML tags are allowed
BLEACH_ALLOWED_TAGS = [
    "code",
    "span",
    "p",
    "ul",
    "ol",
    "li",
    "a",
    "em",
    "strong",
    "u",
    "b",
    "i",
    "pre",
    "sub",
    "sup",
    "del",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "br",
    "table",
    "tbody",
    "tr",
    "th",
    "td",
    "thead",
    "tfoot",
    "caption",
]
# Which HTML attributes are allowed
BLEACH_ALLOWED_ATTRIBUTES = ["href", "title", "style", "class", "src", "colspan"]
# Which CSS properties are allowed in 'style' attributes (assuming style is an allowed attribute)
BLEACH_ALLOWED_STYLES = [
    "color",
    "background-color",
    "font-family",
    "font-weight",
    "text-decoration",
    "font-variant",
    "border",
]
# Which protocols (and pseudo-protocols) are allowed in 'src' attributes (assuming src is an allowed attribute)
BLEACH_ALLOWED_PROTOCOLS = ["http", "https", "data"]
# Strip unknown tags if True, replace with HTML escaped characters if False
BLEACH_STRIP_TAGS = True
# Strip HTML comments, or leave them in.
BLEACH_STRIP_COMMENTS = True

# Ghostwriter API Configuration
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # 'rest_framework.authentication.TokenAuthentication',
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        # 'rest_framework_api_key.permissions.HasAPIKey',
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
}

GRAPHQL_JWT = {
    "JWT_AUTH_HEADER_PREFIX": "Bearer",
    "JWT_VERIFY": True,
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
    "JWT_EXPIRATION_DELTA": timedelta(minutes=15),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days=7),
    "JWT_AUDIENCE": "Ghostwriter",
    "JWT_SECRET_KEY": env(
        "DJANGO_JWT_SECRET_KEY",
        default="Vso7i8BApwA6km4L50PFRvqcTtGZHLrC1pnKLCXqfTWifhjbGq4nTd6ZrDH2Iobe",
    ),
    "JWT_ALGORITHM": "HS256",
}

HASURA_ACTION_SECRET = env(
    "HASURA_ACTION_SECRET",
    default="changeme",
)

GRAPHQL_HOST = env("HASURA_GRAPHQL_SERVER_HOSTNAME", default="graphql_engine")

# Health Checks
# ------------------------------------------------------------------------------
HEALTH_CHECK = {
    "DISK_USAGE_MAX": env("HEALTHCHECK_DISK_USAGE_MAX", default=90),
    "MEMORY_MIN": env("HEALTHCHECK_MEM_MIN", default=100),
}
REDIS_URL = env("REDIS_URL", default="redis://redis:6379")

# Tagging
# ------------------------------------------------------------------------------
TAGGIT_CASE_INSENSITIVE = True


def include_settings(py_glob):
    """
    Includes a glob of Python settings files.
    The files will be sorted alphabetically.
    """
    import sys
    import os
    import glob
    from importlib.util import module_from_spec, spec_from_file_location

    # Get caller's global scope
    scope = sys._getframe(1).f_globals

    including_path = scope["__file__"].rstrip("c")
    including_dir = os.path.dirname(including_path)
    py_glob_rel = os.path.join(including_dir, py_glob)

    for relpath in sorted(glob.glob(py_glob_rel)):
        # Read and execute files
        with open(relpath, "rb") as f:
            contents = f.read()
        compiled = compile(contents, relpath, "exec")
        # Use of `exec` is typically dangerous, but we're only executing our own settings files
        # The settings files are user controlled, but any danger represented by executing them also applies to executing the main settings files
        # The primary concern is an admin could unwittingly execute a malicious settings file they did not realize was present
        # However, an admin could also unwittingly run a malicious command in the main settings file
        exec(compiled, scope)

        # Adds dummy module to sys.modules so runserver will reload if they change
        rel_path = os.path.relpath(including_path)
        module_name = "_settings_include.{0}".format(
            rel_path[: rel_path.rfind(".")].replace("/", "."),
        )

        spec = spec_from_file_location(module_name, including_path)
        module = module_from_spec(spec)
        sys.modules[module_name] = module
