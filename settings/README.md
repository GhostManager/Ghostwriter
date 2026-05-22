# Custom Django Settings Directory

This directory is for custom Django configuration files that will be loaded by Ghostwriter.

## Purpose

When using Ghostwriter with published container images (prod mode), you don't have a local
codebase with the config/settings/production.d directory. This settings directory serves the
same purpose, allowing you to customize Django settings without modifying the container images.

## Usage

Create Python files in this directory to override or extend Django settings. Files are loaded
in alphabetical order, so you can use number prefixes to control the loading sequence.

### File Naming Convention

Use descriptive names with optional number prefixes:
- `1-sso-config.py`
- `2-mail-config.py`
- `3-custom-settings.py`

### Example: SSO Configuration

Create a file named `1-sso-provider.py` with content like:

```python
# Provider(s) configuration
SOCIALACCOUNT_PROVIDERS = {
    "microsoft": {
        "APP": {
            "client_id": "YOUR_CLIENT_ID",
            "secret": "YOUR_SECRET",
        }
    },
}

# Extend the installed apps with the SSO app for your provider(s)
SSO_PROVIDERS = ["allauth.socialaccount.providers.microsoft"]
INSTALLED_APPS = INSTALLED_APPS + SSO_PROVIDERS
```

### Example: Email Configuration

Create a file named `2-mail-config.py` with content like:

```python
# Email backend configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "your-email@example.com"
EMAIL_HOST_PASSWORD = "your-password"
DEFAULT_FROM_EMAIL = "noreply@example.com"
```

## Important Notes

- These settings files are only loaded in **prod mode** (published container images)
- For local-dev or local-prod modes, use the config/settings/local.d or production.d directories
  in your local Ghostwriter codebase instead
- Files must be valid Python syntax
- Settings defined here override settings from the base configuration
- Restart your containers after adding or modifying settings files

## Security

This directory has restrictive permissions (0700) to protect sensitive configuration data.
Only the owner can read, write, or traverse this directory.

## Documentation

For more information, see the Ghostwriter documentation:
https://www.ghostwriter.wiki/
