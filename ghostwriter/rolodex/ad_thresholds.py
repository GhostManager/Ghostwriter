"""Shared constants for configurable Active Directory CAP thresholds."""

# Default threshold definitions used for CAP generation. Values are expressed as
# floats and interpreted according to ``threshold_type``.
AD_THRESHOLD_DEFAULTS = {
    "min_enabled_ratio": {
        "label": "Minimum enabled account ratio",
        "issue": "Number of Disabled Accounts",
        "threshold_type": "min_ratio",
        "value": 0.9,
    },
    "generic_accounts_pct": {
        "label": "Generic accounts percentage of enabled accounts",
        "issue": "Number of 'Generic Accounts'",
        "threshold_type": "percent_of_enabled",
        "value": 0.05,
    },
    "generic_logins_pct": {
        "label": "Generic logins percentage of enabled accounts",
        "issue": "Number of Systems with Logged in Generic Accounts",
        "threshold_type": "percent_of_enabled",
        "value": 0.05,
    },
    "inactive_accounts_pct": {
        "label": "Inactive accounts percentage of enabled accounts",
        "issue": "Potentially Inactive Accounts",
        "threshold_type": "percent_of_enabled",
        "value": 0.05,
    },
    "passwords_never_exp_pct": {
        "label": "Passwords that never expire percentage of enabled accounts",
        "issue": "Accounts with Passwords that Never Expire",
        "threshold_type": "percent_of_enabled",
        "value": 0.05,
    },
    "exp_passwords_pct": {
        "label": "Expired passwords percentage of enabled accounts",
        "issue": "Accounts with Expired Passwords",
        "threshold_type": "percent_of_enabled",
        "value": 0.05,
    },
    "domain_admin_pct": {
        "label": "Domain Admins percentage of enabled accounts",
        "issue": "Number of Domain Admins",
        "threshold_type": "percent_of_enabled",
        "value": 0.005,
    },
    "ent_admin_absolute": {
        "label": "Enterprise Admins absolute threshold",
        "issue": "Number of Enterprise Admins",
        "threshold_type": "absolute",
        "value": 1,
    },
}

AD_THRESHOLD_KEY_CHOICES = [(key, meta["label"]) for key, meta in AD_THRESHOLD_DEFAULTS.items()]

AD_THRESHOLD_TYPE_CHOICES = (
    ("percent_of_enabled", "Percent of enabled accounts"),
    ("min_ratio", "Minimum ratio"),
    ("absolute", "Absolute count"),
)
