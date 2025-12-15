"""This contains utilities and values used by template linting."""

from ghostwriter.reporting.models import RiskScoreRangeMapping
from ghostwriter.rolodex.data_parsers import normalize_nexpose_artifacts_map

# Example JSON reporting data for loading into templates for rendering tests
LINTER_CONTEXT = {
    "report_date": "Mar. 25, 2021",
    "tags": ["tag1", "tag2", "tag3"],
    "mk_logo": "",
    "project": {
        "id": 1,
        "name": "2021-03-01 Kabletown, Inc. Red Team (KABLE-01)",
        "type": "Red Team",
        "start_date": "Mar. 1, 2021",
        "start_month": "March",
        "start_day": 1,
        "start_year": 2021,
        "end_date": "Jun. 25, 2021",
        "end_month": "June",
        "end_day": 25,
        "end_year": 2021,
        "codename": "KABLE-01",
        "timezone": "America/Los_Angeles",
        "note": "<p>This is an assessment for Kabletown but targets NBC assets. The goal is to answer specific questions prior to Kabletown absorbing NBC.</p>",
        "note_rt": "",
        "slack_channel": "#ghostwriter",
        "complete": False,
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "tags": ["tag1", "tag2", "tag3"],
        "ai_review": {
            "osint_rt": "<p>OSINT executive summary</p>",
            "dns_rt": "<p>DNS best practice summary</p>",
            "external_nexpose_rt": "<p>External Nexpose vulnerability overview</p>",
            "internal_nexpose_rt": "<p>Internal Nexpose vulnerability overview</p>",
            "iot_iomt_nexpose_rt": "<p>IoT/IoMT Nexpose vulnerability overview</p>",
            "endpoint_rt": "<p>Endpoint security software and WiFi review</p>",
            "snmp_rt": "<p>SNMP default string review summary</p>",
            "sql_rt": "<p>SQL default credential review summary</p>",
            "firewall_rt": "<p>Firewall configuration and rule review summary</p>",
            "wireless_rt": "<p>Wireless network assessment summary</p>",
            "cloud_management_rt": "<p>Cloud management configuration summary</p>",
            "iam_management_rt": "<p>M365 IAM configuration summary</p>",
            "system_configuration_rt": "<p>System configuration benchmark summary</p>",
            "web_rt": "<p>Web application findings summary</p>",
            "ad_rt": "<p>Active Directory review summary</p>",
            "password_rt": "<p>Password policy and cracking summary</p>",
        },
        "scoping": {
            "external": {
                "selected": True,
                "osint": True,
                "dns": True,
                "nexpose": False,
                "web": True,
            },
            "internal": {
                "selected": True,
                "nexpose": True,
                "iot_iomt": False,
                "endpoint": True,
                "snmp": False,
                "sql": True,
            },
            "iam": {
                "selected": True,
                "ad": True,
                "password": True,
            },
            "wireless": {
                "selected": True,
                "walkthru": True,
                "segmentation": False,
            },
            "firewall": {
                "selected": True,
                "os": True,
                "configuration": True,
            },
            "cloud": {
                "selected": True,
                "cloud_management": True,
                "iam_management": True,
                "system_configuration": True,
            },
            "cloud_management": True,
            "iam_management": True,
            "system_configuration": True,
        },
        "risks": {
            "overall_risk": "Medium",
            "overall_risk_rt": "Medium",
            "external": "Low",
            "external_rt": "Low",
            "internal": "High",
            "internal_rt": "High",
            "wireless": "Medium",
            "wireless_rt": "Medium",
            "firewall": "High",
            "firewall_rt": "High",
            "osint": "High",
            "osint_rt": "High",
            "dns": "Medium",
            "dns_rt": "Medium",
            "external_nexpose": "Low",
            "external_nexpose_rt": "Low",
            "web": "Medium",
            "web_rt": "Medium",
            "cloud_config": "Medium",
            "cloud_config_rt": "Medium",
            "system_config": "Low",
            "system_config_rt": "Low",
            "cloud_management": "Medium",
            "cloud_management_rt": "Medium",
            "iam_management": "Medium",
            "iam_management_rt": "Medium",
            "system_configuration": "Low",
            "system_configuration_rt": "Low",
            "ad": "High",
            "ad_rt": "High",
            "internal_nexpose": "High",
            "internal_nexpose_rt": "High",
            "endpoint": "Medium",
            "endpoint_rt": "Medium",
            "snmp": "Low",
            "snmp_rt": "Low",
            "sql": "High",
            "sql_rt": "High",
            "iam": "High",
            "iam_rt": "High",
            "password": "Medium",
            "password_rt": "Medium",
            "cloud": "Medium",
            "cloud_rt": "Medium",
            "configuration": "Low",
            "configuration_rt": "Low",
        },
        "workbook_data": {
            "client": {
                "name": "Example Client Name",
                "short_name": "ECN",
                "primary_contact": "Hank Hooper",
                "primary_contact_email": "dad@kabletown.family",
            },
            "general": {
                "firewall": "2025-01-27",
                "wireless": "2025-01-26",
                "external_start": "2025-01-10",
                "external_end": "2025-01-14",
                "internal_start": "2025-01-20",
                "internal_end": "2025-01-25",
                "cloud_provider": "AWS",
                "internal_subnets": "10.0.0.0/16, 192.168.5.0/24",
            },
            "ad": {
                "domains": [
                    {
                        "domain": "corp.example.com",
                        "ent_admins": 2,
                        "domain_admins": 5,
                        "exp_passwords": 12,
                        "old_passwords": 22,
                        "generic_logins": 3,
                        "total_accounts": 245,
                        "enabled_accounts": 220,
                        "generic_accounts": 6,
                        "inactive_accounts": 15,
                        "passwords_never_exp": 8,
                        "functionality_level": "Windows Server 2019",
                        "old_password_counts": {
                            "never": 7,
                            "30_days": 30,
                            "90_days": 25,
                            "180_days": 15,
                            "1_year": 10,
                            "2_year": 8,
                            "3_year": 5,
                            "compliant": 145,
                        },
                        "inactive_account_counts": {
                            "never": 3,
                            "30_days": 15,
                            "90_days": 10,
                            "180_days": 5,
                            "1_year": 5,
                            "2_year": 4,
                            "3_year": 3,
                            "active": 200,
                        },
                    }
                ]
            },
            "dns": {
                "unique": 12,
                "records": [
                    {
                        "domain": "example.com",
                        "total": 15,
                        "zone_transfer": "no",
                    },
                    {
                        "domain": "test.example.com",
                        "total": 7,
                        "zone_transfer": "yes",
                    },
                ],
            },
            "sql": {
                "subnets": "3 (Platinum)",
                "db_types": "MSSQL, MySQL, Oracle",
                "total_open": 18,
                "weak_creds": 4,
                "unsupported_dbs": {"count": 3, "confirm": "true"},
            },
            "web": {
                "sites": [
                    {
                        "url": "https://portal.example.com",
                        "unique_low": 5,
                        "unique_med": 7,
                        "unique_high": 3,
                    },
                    {
                        "url": "https://intranet.example.com",
                        "unique_low": 2,
                        "unique_med": 4,
                        "unique_high": 1,
                    },
                ],
                "combined_unique": 22,
                "combined_unique_low": 7,
                "combined_unique_med": 11,
                "combined_unique_high": 4,
            },
            "snmp": {
                "subnets": "3 (Platinum)",
                "total_strings": 42,
                "total_systems": 15,
                "read_write_access": "yes",
            },
            "osint": {
                "total_ips": 52,
                "total_cloud": 18,
                "total_leaks": 3,
                "total_squat": 7,
                "total_buckets": 4,
                "total_domains": 45,
                "total_hostnames": 73,
            },
            "endpoint": {
                "domains": [
                    {
                        "domain": "corp.example.com",
                        "access_pct": "96.47%",
                        "open_wifi": 3,
                        "systems_ood": 45,
                        "total_computers": 850,
                        "audited_computers": 820,
                        "usb_control_indication": "yes",
                    },
                    {
                        "domain": "lab.example.com",
                        "access_pct": "83.33%",
                        "open_wifi": 1,
                        "systems_ood": 10,
                        "total_computers": 120,
                        "audited_computers": 100,
                        "usb_control_indication": "no",
                    },
                ]
            },
            "firewall": {
                "unique": 12,
                "devices": [
                    {
                        "device": "Edge-FW01",
                        "name": "Edge-FW01",
                        "ood": "yes",
                        "total_low": 3,
                        "total_med": 5,
                        "total_high": 2,
                    },
                    {
                        "device": "Core-FW02",
                        "name": "Core-FW02",
                        "ood": "no",
                        "total_low": 4,
                        "total_med": 3,
                        "total_high": 0,
                    },
                ],
                "unique_low": 4,
                "unique_med": 6,
                "unique_high": 2,
                "majority_type": "Rules",
                "majority_count": 8,
                "minority_type": "Complexity",
                "minority_count": 3,
                "complexity_count": 5,
            },
            "password": {
                "policies": [
                    {
                        "domain_name": "corp.example.com",
                        "history": 24,
                        "history_rt": "<p>24</p>",
                        "max_age": 90,
                        "max_age_rt": "<p>90</p>",
                        "min_age": 1,
                        "min_age_rt": "<p>1</p>",
                        "min_length": 12,
                        "min_length_rt": "<p>12</p>",
                        "lockout_reset": 30,
                        "lockout_reset_rt": "<p>30</p>",
                        "lockout_duration": 30,
                        "lockout_duration_rt": "<p>30</p>",
                        "lockout_threshold": 5,
                        "lockout_threshold_rt": "<p>5</p>",
                        "complexity_enabled": "yes",
                        "complexity_enabled_rt": "<p>yes</p>",
                        "lanman_stored": "yes",
                        "mfa_required": "yes",
                        "enabled_accounts": 245,
                        "passwords_cracked": 17,
                        "strong_passwords": 210,
                        "admin_cracked": {"count": 2, "confirm": "yes"},
                        "password_pattern": {
                            "confirm": "yes",
                            "passwords": [
                                {"password": "Winter2023!", "count": 6},
                                {"password": "Welcome1", "count": 3},
                            ],
                        },
                        "fgpp": [
                            {
                                "fgpp_name": "Tier0Admins",
                                "history": 24,
                                "history_rt": "<p>24</p>",
                                "max_age": 45,
                                "max_age_rt": "<p>45</p>",
                                "min_age": 1,
                                "min_age_rt": "<p>1</p>",
                                "min_length": 14,
                                "min_length_rt": "<p>14</p>",
                                "lockout_reset": 15,
                                "lockout_reset_rt": "<p>15</p>",
                                "lockout_duration": 15,
                                "lockout_duration_rt": "<p>15</p>",
                                "lockout_threshold": 3,
                                "lockout_threshold_rt": "<p>3</p>",
                                "complexity_enabled": "yes",
                                "complexity_enabled_rt": "<p>yes</p>",
                            },
                            {
                                "fgpp_name": "ServiceAccounts",
                                "history": 5,
                                "history_rt": "<p>5</p>",
                                "max_age": 365,
                                "max_age_rt": "<p>365</p>",
                                "min_age": 0,
                                "min_age_rt": "<p>0</p>",
                                "min_length": 20,
                                "min_length_rt": "<p>20</p>",
                                "lockout_reset": 0,
                                "lockout_reset_rt": "<p>0</p>",
                                "lockout_duration": 0,
                                "lockout_duration_rt": "<p>0</p>",
                                "lockout_threshold": 0,
                                "lockout_threshold_rt": "<p>0</p>",
                                "complexity_enabled": "no",
                                "complexity_enabled_rt": "<p>no</p>",
                            },
                        ],
                    }
                ]
            },
            "wireless": {
                "psk_count": 12,
                "weak_psks": "no",
                "open_count": 5,
                "rogue_count": 2,
                "hidden_count": 3,
                "rogue_signals": "yes",
                "internal_access": "yes",
                "802_1x_used": "no",
                "wep_inuse": {"confirm": "no", "key_cracked": None},
            },
            "report_card": {
                "overall": "A",
                "overall_rt": "A",
                "overall_grade_rt": "A",
                "external": "A",
                "external_rt": "A",
                "internal": "B+",
                "internal_rt": "B+",
                "firewall": "B",
                "firewall_rt": "B",
                "wireless": "A-",
                "wireless_rt": "A-",
                "iam": "B+",
                "iam_rt": "B+",
                "cloud": "B",
                "cloud_rt": "B",
            },
            "iam_cloud_config": {"pass": 6, "fail": 1},
            "cloud_config": {"pass": 85, "fail": 12},
            "system_config": {
                "total_pass": 145,
                "total_fail": 23,
                "unique_pass": 110,
                "unique_fail": 18,
            },
            "external_nexpose": {
                "total": 230,
                "unique": 145,
                "total_low": 121,
                "total_med": 84,
                "total_high": 25,
                "majority_type": "OOD",
                "minority_type": "ISC",
                "unique_high_med": 62,
                "unique_majority": 38,
                "unique_minority": 9,
                "unique_majority_sub": 14,
                "unique_majority_sub_info": "Version 2.4.x instances with outdated modules",
            },
            "internal_nexpose": {
                "total": 230,
                "unique": 145,
                "total_low": 121,
                "total_med": 84,
                "total_high": 25,
                "majority_type": "ISC",
                "minority_type": "OOD",
                "unique_high_med": 62,
                "unique_majority": 38,
                "unique_minority": 9,
                "unique_majority_sub": 14,
                "unique_majority_sub_info": "Version 2.4.x instances with outdated modules",
            },
            "iot_iomt_nexpose": {
                "total": 230,
                "unique": 145,
                "total_low": 121,
                "total_med": 84,
                "total_high": 25,
                "majority_type": "OOD",
                "minority_type": "Even",
                "unique_high_med": 62,
                "unique_majority": 38,
                "unique_minority": 9,
                "unique_majority_sub": 14,
                "unique_majority_sub_info": "Version 2.4.x instances with outdated modules",
            },
            "external_internal_grades": {
                "external": {
                    "grade": "B+",
                    "grade_rt": "B+",
                    "total": 3.0,
                    "dns": {"risk": "Medium", "risk_rt": "Medium", "score": 3.2},
                    "web": {"risk": "Low", "risk_rt": "Low", "score": 1.7},
                    "osint": {"risk": "High", "risk_rt": "High", "score": 4.5},
                    "nexpose": {"risk": "Medium", "risk_rt": "Medium", "score": 2.8},
                    "iot_iomt": {"risk": "Low", "risk_rt": "Low", "score": 2.2},
                },
                "internal": {
                    "grade": "B",
                    "grade_rt": "B",
                    "total": 3.3,
                    "iam": {"risk": "High", "risk_rt": "High", "score": 4.2},
                    "iot_iomt": {"risk": "Medium", "risk_rt": "Medium", "score": 3.4},
                    "sql": {"risk": "High", "risk_rt": "High", "score": 4.0},
                    "snmp": {"risk": "Low", "risk_rt": "Low", "score": 2.8},
                    "cloud": {"risk": "Medium", "risk_rt": "Medium", "score": 3.3},
                    "endpoint": {"risk": "Medium", "risk_rt": "Medium", "score": 3.0},
                    "password": {"risk": "Medium", "risk_rt": "Medium", "score": 3.9},
                    "configuration": {"risk": "Medium", "risk_rt": "Medium", "score": 3.1},
                    "nexpose": {"risk": "High", "risk_rt": "High", "score": 4.4},
                },
                "iam": {
                    "grade": "B+",
                    "grade_rt": "B+",
                    "total": 3.1,
                    "ad": {"risk": "High", "risk_rt": "High", "score": 4.0},
                    "password": {"risk": "Medium", "risk_rt": "Medium", "score": 3.2},
                },
                "wireless": {
                    "grade": "A-",
                    "grade_rt": "A-",
                    "total": 2.4,
                    "walkthru": {"risk": "Low", "risk_rt": "Low", "score": 2.0},
                    "segmentation": {"risk": "Medium", "risk_rt": "Medium", "score": 2.8},
                },
                "firewall": {
                    "grade": "B",
                    "grade_rt": "B",
                    "total": 3.0,
                    "os": {"risk": "Medium", "risk_rt": "Medium", "score": 3.1},
                    "configuration": {"risk": "Medium", "risk_rt": "Medium", "score": 2.9},
                },
                "cloud": {
                    "grade": "B",
                    "grade_rt": "B",
                    "total": 3.2,
                    "cloud_management": {"risk": "Medium", "risk_rt": "Medium", "score": 3.0},
                    "iam_management": {"risk": "Medium", "risk_rt": "Medium", "score": 3.4},
                    "system_configuration": {"risk": "Medium", "risk_rt": "Medium", "score": 3.2},
                },
            },
        },
        "data_responses": {
            "executive_summary": "Client is preparing for an acquisition in Q3.",
            "critical_contacts": [
                "hank.hooper@example.com",
                "jack.donaghy@example.com",
            ],
            "general": {
                "general_first_ca": "no",
                "general_scope_changed": "yes",
                "general_anonymous_ephi": "no",
                "scope_count": 3,
                "scope_string": (
                    "External network and systems, Internal network and systems and "
                    "Firewall configuration(s) & rules"
                ),
            },
            "intelligence": {
                "osint_squat_concern": "example.com",
                "osint_bucket_risk": "High",
                "osint_leaked_creds_risk": "Medium",
                "osint_bucket_risk_rt": "High",
                "osint_leaked_creds_risk_rt": "Medium",
            },
            "iot_iomt": {"iot_testing_confirm": "yes"},
            "dns": {
                "zone_trans": 1,
                "entries": [
                    {
                        "domain": "example.com",
                        "soa_fields": ["serial", "refresh"],
                    }
                ],
                "unique_soa_fields": ["serial", "refresh"],
                "soa_field_cap_map": {
                    "serial": "Update to match the 'YYYYMMDDnn' scheme",
                    "refresh": "Update to a value between 1200 and 43200 seconds",
                },
            },
            "wireless": {
                "segmentation_ssids": ["Guest", "Corp", "Production"],
                "psk_risk": "medium",
                "open_risk": "high",
                "rogue_risk": "medium",
                "hidden_risk": "low",
                "psk_risk_rt": "medium",
                "open_risk_rt": "high",
                "rogue_risk_rt": "medium",
                "hidden_risk_rt": "low",
                "psk_rotation_concern": "yes",
                "segmentation_tested": True,
                "psk_weak_reasons": "to short and not enough entropy",
                "psk_masterpass": "no",
            },
            "cloud_config_risk": "low",
            "system_config_risk": "medium",
            "ad": {
                "entries": [
                    {
                        "domain": "corp.example.com",
                        "domain_admins": "high",
                        "old_passwords": "low",
                        "generic_logins": "medium",
                        "generic_accounts": "high",
                        "disabled_accounts": "high",
                        "enterprise_admins": "medium",
                        "expired_passwords": "low",
                        "inactive_accounts": "medium",
                        "passwords_never_expire": "low",
                    }
                ],
                "domains_str": "'corp.example.com'",
                "enabled_count_str": "220",
                "da_count_str": "5",
                "ea_count_str": "2",
                "ep_count_str": "12",
                "ne_count_str": "8",
                "ia_count_str": "15",
                "ga_count_str": "6",
                "gl_count_str": "3",
                "da_risk_string": "High",
                "ea_risk_string": "Medium",
                "ep_risk_string": "Low",
                "ne_risk_string": "Low",
                "ia_risk_string": "Medium",
                "ga_risk_string": "High",
                "gl_risk_string": "Medium",
                "da_risk_string_rt": "High",
                "ea_risk_string_rt": "Medium",
                "ep_risk_string_rt": "Low",
                "ne_risk_string_rt": "Low",
                "ia_risk_string_rt": "Medium",
                "ga_risk_string_rt": "High",
                "gl_risk_string_rt": "Medium",
                "old_domains_string": "'legacy.local' and 'ancient.local'",
                "old_domains_str": "'legacy.local'/'ancient.local'",
                "old_domains_count": 2,
                "risk_contrib": [
                    "the number of Domain Admin accounts",
                    "the number of potentially generic accounts",
                    "the number of disabled accounts",
                ],
                "domain_metrics": [
                    {
                        "domain_name": "corp.example.com",
                        "disabled_count": 25,
                        "disabled_pct": 10.2,
                        "old_pass_pct": 8.2,
                        "ia_pct": 4.1,
                    },
                    {
                        "domain_name": "lab.example.com",
                        "disabled_count": 12,
                        "disabled_pct": 9.2,
                        "old_pass_pct": 11.5,
                        "ia_pct": 6.3,
                    },
                ],
                "disabled_account_string": "25 and 12",
                "disabled_account_pct_string": "10.2% and 9.2%",
                "old_password_string": "18 and 12",
                "old_password_pct_string": "8.2% and 11.5%",
                "inactive_accounts_string": "10 and 8",
                "inactive_accounts_pct_string": "4.1% and 6.3%",
                "domain_admins_string": "5 and 3",
                "ent_admins_string": "2 and 1",
                "exp_passwords_string": "12 and 8",
                "never_expire_string": "8 and 5",
                "generic_accounts_string": "6 and 4",
                "generic_logins_string": "3 and 2",
            },
            "password": {
                "password_additional_controls": "yes",
                "password_enforce_mfa_all_accounts": "no",
                "hashes_obtained": "yes",
                "entries": [
                    {
                        "domain": "corp.example.com",
                        "risk": "medium",
                        "bad_pass": True,
                        "bad_policy_fields": ["max_age", "complexity_enabled"],
                        "policy_cap_values": {"max_age": 90, "complexity_enabled": "TRUE"},
                        "fgpp_bad_fields": {
                            "Tier0Admins": ["max_age", "lockout_reset", "lockout_duration", "complexity_enabled"],
                            "ServiceAccounts": [
                                "history",
                                "max_age",
                                "min_age",
                                "lockout_threshold",
                                "lockout_reset",
                            ],
                        },
                        "fgpp_cap_values": {
                            "Tier0Admins": {
                                "max_age": 45,
                                "lockout_reset": 15,
                                "lockout_duration": 15,
                                "complexity_enabled": "TRUE",
                            },
                            "ServiceAccounts": {
                                "history": 5,
                                "max_age": 365,
                                "min_age": 0,
                                "lockout_threshold": 0,
                                "lockout_reset": 0,
                            },
                        },
                    },
                    {"domain": "lab.example.com", "risk": "high", "bad_pass": False},
                ],
                "domains_str": "'corp.example.com'/'lab.example.com'",
                "cracked_count_str": "17/9",
                "cracked_risk_string": "Medium/High",
                "cracked_risk_string_rt": "Medium/High",
                "cracked_finding_string": "17 and 9",
                "enabled_count_string": "220 and 150",
                "admin_cracked_string": "2 and 1",
                "admin_cracked_doms": "'corp.example.com' and 'lab.example.com'",
                "lanman_list_string": "'corp.example.com'",
                "no_fgpp_string": "'lab.example.com'",
                "bad_pass_count": 2,
                "policy_cap_fields": [
                    "max_age",
                    "complexity_enabled",
                    "lockout_reset",
                    "lockout_duration",
                    "history",
                    "min_age",
                    "lockout_threshold",
                ],
                "policy_cap_map": {
                    "corp.example.com": {
                        "policy": {
                            "score": 4,
                            "max_age": (
                                "Change 'Maximum Age' from 90 to == 0 to align with NIST recommendations "
                                "to not force users to arbitrarily change passwords based solely on age"
                            ),
                            "complexity_enabled": (
                                "Change 'Complexity Required' from TRUE to FALSE and implement additional password selection "
                                "controls such as blacklists"
                            ),
                        },
                        "fgpp": {
                            "Tier0Admins": {
                                "score": 4,
                                "max_age": (
                                    "Change 'Maximum Age' from 45 to == 0 to align with NIST recommendations "
                                    "to not force users to arbitrarily change passwords based solely on age"
                                ),
                                "lockout_reset": "Change 'Lockout Reset' from 15 to >= 30",
                                "lockout_duration": "Change 'Lockout Duration' from 15 to >= 30 or admin unlock",
                                "complexity_enabled": (
                                    "Change 'Complexity Required' from TRUE to FALSE and implement additional password selection "
                                    "controls such as blacklists"
                                ),
                            },
                            "ServiceAccounts": {
                                "score": 4,
                                "history": "Change 'History' from 5 to >= 10",
                                "max_age": (
                                    "Change 'Maximum Age' from 365 to == 0 to align with NIST recommendations "
                                    "to not force users to arbitrarily change passwords based solely on age"
                                ),
                                "min_age": "Change 'Minimum Age' from 0 to >= 1 and < 7",
                                "lockout_threshold": "Change 'Lockout Threshold' from 0 to > 0 and <= 6",
                                "lockout_reset": "Change 'Lockout Reset' from 0 to >= 30",
                            },
                        },
                    }
                },
                "policy_cap_context": {
                    "corp.example.com": {
                        "policy": {"max_age": 90, "complexity_enabled": "TRUE"},
                        "fgpp": {
                            "Tier0Admins": {
                                "max_age": 45,
                                "lockout_reset": 15,
                                "lockout_duration": 15,
                                "complexity_enabled": "TRUE",
                            },
                            "ServiceAccounts": {
                                "history": 5,
                                "max_age": 365,
                                "min_age": 0,
                                "lockout_threshold": 0,
                                "lockout_reset": 0,
                            },
                        },
                    }
                },
            },
            "endpoint": {
                "entries": [
                    {
                        "domain": "corp.example.com",
                        "open_wifi": "low",
                        "av_gap": "medium",
                    },
                    {
                        "domain": "lab.example.com",
                        "open_wifi": "high",
                        "av_gap": "high",
                    },
                ],
                "domains_str": "corp.example.com/lab.example.com",
                "ood_count_str": "45/10",
                "wifi_count_str": "3/1",
                "ood_risk_string": "Medium/High",
                "wifi_risk_string": "Low/High",
                "ood_risk_string_rt": "Medium/High",
                "wifi_risk_string_rt": "Low/High",
            },
            "firewall": {
                "entries": [
                    {"name": "Edge-FW01", "type": "Next-Gen"},
                    {"name": "Core-FW02", "type": "Appliance"},
                ],
                "ood_name_list": "'Edge-FW01'",
                "ood_count": 1,
                "firewall_periodic_reviews": "yes",
            },
            "overall_risk": {
                "major_issues": [
                    "Legacy firewall configurations",
                    "Privileged account sprawl",
                ]
            },
            "executive_summary": "Client is preparing for an acquisition in Q3.",
            "critical_contacts": [
                "hank.hooper@example.com",
                "jack.donaghy@example.com",
            ],
            "has_internal_lab": "yes",
        },
        "data_artifacts": {
            "dns_issues": [
                {
                    "domain": "example.com",
                    "issues": [
                        {
                            "issue": "The domain does not have an SPF record",
                            "finding": "email delivery for the domain",
                            "recommendation": "consider implementing a SPF record",
                            "cap": "Consider implementing a SPF record",
                            "impact": "Lack of SPF allows attackers to spoof emails from the domain, enabling phishing or spam campaigns.",
                        }
                    ],
                }
            ],
            "dns_findings": {
                "example.com": [
                    {
                        "Record": "TXT",
                        "Status": "FAIL",
                        "Test": "SPF Record Present",
                        "Details": "No SPF record configured for example.com.",
                    },
                    {
                        "Record": "MX",
                        "Status": "WARN",
                        "Test": "MX Record TTL",
                        "Details": "TTL below recommended minimum of 3600 seconds.",
                    },
                ]
            },
            "web_issues": {
                "low_sample_string": "",
                "med_sample_string": "'Reveals stack traces that aid targeted exploitation attempts.'",
                "ai_response": None,
                "high": {
                    "total_unique": 2,
                    "items": [
                        {
                            "issue": "Reflected Cross-Site Scripting",
                            "impact": "Enables theft of user credentials through malicious scripts.",
                            "count": 3,
                        },
                        {
                            "issue": "Missing HTTP security headers",
                            "impact": "Allows clickjacking and content injection attacks against users.",
                            "count": 2,
                        },
                    ],
                },
                "med": {
                    "total_unique": 1,
                    "items": [
                        {
                            "issue": "Verbose error messages exposed",
                            "impact": "Reveals stack traces that aid targeted exploitation attempts.",
                            "count": 1,
                        }
                    ],
                },
                "low": {"total_unique": 0, "items": []},
            },
            "web_metrics": {
                "summary": {
                    "total": 7,
                    "unique": 4,
                    "total_high": 2,
                    "total_med": 3,
                    "total_low": 2,
                    "unique_high": 2,
                    "unique_med": 1,
                    "unique_low": 1,
                    "host_risk_counts": [
                        {"host": "portal.example.com", "high": 2, "medium": 1, "low": 0},
                        {"host": "intranet.example.com", "high": 0, "medium": 1, "low": 1},
                    ],
                    "uniquelow": 1,
                },
                "unique_issues": [
                    {
                        "Issue": "Missing HTTP security headers",
                        "Impact": "Allows clickjacking attacks",
                        "Risk": "Medium",
                        "Score": 6.5,
                    },
                    {
                        "Issue": "Reflected Cross-Site Scripting",
                        "Impact": "Session theft",
                        "Risk": "High",
                        "Score": 8.1,
                    },
                ],
                "all_issues": [
                    {
                        "Issue": "Missing HTTP security headers",
                        "Risk": "Medium",
                        "Score": 6.5,
                        "Host": "portal.example.com",
                        "Path": "/",
                    },
                    {
                        "Issue": "Reflected Cross-Site Scripting",
                        "Risk": "High",
                        "Score": 8.6,
                        "Host": "portal.example.com",
                        "Path": "/login",
                    },
                ],
                "high_issues": [
                    {
                        "Issue": "Reflected Cross-Site Scripting",
                        "Risk": "High",
                        "Score": 8.6,
                        "Host": "portal.example.com",
                        "Path": "/login",
                    }
                ],
                "med_issues": [
                    {
                        "Issue": "Missing HTTP security headers",
                        "Risk": "Medium",
                        "Score": 6.5,
                        "Host": "portal.example.com",
                        "Path": "/",
                    }
                ],
                "low_issues": [
                    {
                        "Issue": "Verbose error messages exposed",
                        "Risk": "Low",
                        "Score": 3.5,
                        "Host": "api.example.com",
                        "Path": "/debug",
                    }
                ],
                "top_impacts": [
                    {"impact": "Session hijacking", "count": 3},
                    {"impact": "Information disclosure", "count": 1},
                ],
                "tab_index_entries": [
                    "Unique Issues  -:-  Unique issues found across all scanned systems",
                    "All Issues  -:-  All issues identified.",
                    "High Risk Issues  -:-  All 'High' risk issues identified",
                    "Medium Risk Issues  -:-  All 'Medium' risk issues identified",
                    "Low Risk Issues  -:-  All 'Low' risk issues identified",
                ],
                "xlsx_filename": "burp_data.xlsx",
                "xlsx_base64": "UEsDBBQAAgAIACJwZW5jaABXZWJNZXRyaWNz",
            },
            "web_findings": [
                {
                    "Issue": "Missing HTTP security headers",
                    "Impact": "Clickjacking risk",
                    "Risk": "Medium",
                    "Host": "portal.example.com",
                    "Path": "/",
                    "Score": 6.5,
                },
                {
                    "Issue": "Reflected Cross-Site Scripting",
                    "Impact": "Session hijacking",
                    "Risk": "High",
                    "Host": "portal.example.com",
                    "Path": "/login",
                    "Score": 8.6,
                },
            ],
            "web_cap_map": [
                {
                    "issue": "Missing HTTP security headers",
                    "risk": "Medium",
                    "finding_score": 6.5,
                    "recommendation": "Implement X-Frame-Options, X-Content-Type-Options, and Content-Security-Policy headers.",
                    "score": 4,
                }
            ],
            "web_issue_matrix_gaps": {
                "entries": [
                    {
                        "issue": "Legacy HTTP Authentication",
                        "impact": "Allows brute-force attacks without throttling.",
                        "fix": "Enforce lockouts and enable MFA for the application.",
                    }
                ]
            },
            "external_ips": [
                "203.0.113.10",
                "203.0.113.11",
                "203.0.113.25",
            ],
            "internal_ips": [
                "10.10.10.25",
                "10.20.30.40",
                "172.16.50.5",
            ],
            "firewall_findings": [
                {
                    "Risk": "High",
                    "Issue": "Overly permissive inbound access",
                    "Devices": "Edge-FW01",
                    "Solution": "Review inbound access and enforce least privilege",
                    "Impact": "Increases the exposed attack surface for external actors.",
                    "Details": "Numerous any-to-any rules allow unsolicited ingress.",
                    "Reference": "Vendor advisory",
                    "Score": 8.5,
                    "Accepted": "No",
                    "Type": "Vuln",
                },
                {
                    "Risk": "Medium",
                    "Issue": "Stale decommissioned network objects",
                    "Devices": "Core-FW02",
                    "Solution": "Remove unused objects from policy",
                    "Impact": "Obsolete objects complicate reviews and obscure risky rules.",
                    "Details": "Objects no longer referenced in active rules remain in the configuration.",
                    "Reference": "",
                    "Score": 5.0,
                    "Accepted": "No",
                    "Type": "Config",
                },
            ],
            "firewall_metrics": {
                "summary": {
                    "unique": 2,
                    "unique_high": 1,
                    "unique_med": 1,
                    "unique_low": 0,
                    "rule_count": 1,
                    "config_count": 1,
                    "complexity_count": 0,
                    "vuln_count": 0,
                },
                "devices": [
                    {
                        "device": "Core-FW02",
                        "total_high": 1,
                        "total_med": 1,
                        "total_low": 0,
                        "ood": "no",
                    }
                ],
            },
            "firewall_vulnerabilities": {
                "high": {
                    "total_unique": 1,
                    "items": [
                        {
                            "issue": "Overly permissive inbound access",
                            "impact": "Increases the exposed attack surface for external actors.",
                            "count": 1,
                        }
                    ],
                },
                "med": {
                    "total_unique": 1,
                    "items": [
                        {
                            "issue": "Stale decommissioned network objects",
                            "impact": "Obsolete objects complicate reviews and obscure risky rules.",
                            "count": 1,
                        }
                    ],
                },
                "low": {"total_unique": 0, "items": []},
            },
            "external_nexpose_vulnerabilities": {
                "label": "External Nexpose Vulnerabilities",
                "high": {
                    "total_unique": 4,
                    "items": [
                        {
                            "title": "OpenSSL Padding Oracle (CVE-2016-2107)",
                            "impact": "Allows attackers to decrypt TLS traffic and impersonate the server.",
                            "count": 3,
                        },
                        {
                            "title": "Outdated Apache HTTP Server",
                            "impact": "Enables remote code execution through known exploits.",
                            "count": 2,
                        },
                    ],
                },
                "med": {
                    "total_unique": 2,
                    "items": [
                        {
                            "title": "SMB Signing Not Required",
                            "impact": "Permits man-in-the-middle attacks on SMB sessions.",
                            "count": 4,
                        }
                    ],
                },
                "low": {
                    "total_unique": 0,
                    "items": [],
                },
            },
            "external_nexpose_findings": {
                "findings": [
                    {
                        "Asset IP Address": "203.0.113.10",
                        "Hostname(s)": "edge.example.com",
                        "Service Port": "443",
                        "Protocol": "tcp",
                        "Vulnerability Title": "OpenSSL Padding Oracle (CVE-2016-2107)",
                        "Impact": "Allows attackers to decrypt TLS traffic and impersonate the server.",
                        "Solution": "Update OpenSSL to a supported release.",
                        "Category": "OOD",
                        "Details": "Server negotiates vulnerable OpenSSL build.",
                        "Evidence": "Observed server certificate during scan.",
                        "Detailed Remediation": "Upgrade to OpenSSL 1.1.1 or later.",
                    }
                ],
                "software": [
                    {"Software": "OpenSSL", "Version": "1.0.2", "Instances": 3},
                    {"Software": "Apache HTTPD", "Version": "2.4.38", "Instances": 2},
                ],
            },
            "external_nexpose_metrics": {
                "summary": {
                    "total": 12,
                    "total_high": 4,
                    "total_med": 5,
                    "total_low": 3,
                    "unique": 6,
                    "unique_high": 3,
                    "unique_med": 2,
                    "unique_low": 1,
                    "unique_high_med": 5,
                    "total_ood": 2,
                    "total_isc": 3,
                    "total_iwc": 1,
                    "majority_count": 3,
                    "minority_count": 1,
                },
                "host_counts": [
                    {"host": "edge.example.com", "high": 2, "med": 1, "low": 0},
                    {"host": "vpn.example.com", "high": 1, "med": 2, "low": 1},
                ],
                "top_hosts": [
                    {"host": "edge.example.com", "high": 2, "med": 1, "low": 0, "total": 3, "score": 8},
                    {"host": "vpn.example.com", "high": 1, "med": 2, "low": 1, "total": 4, "score": 7},
                ],
                "top_hosts_high": 3,
                "top_hosts_med": 3,
                "top_hosts_low": 1,
                "top_hosts_total": 7,
                "top_impacts": [
                    {"impact": "Remote code execution", "count": 3},
                    {"impact": "Credential theft", "count": 2},
                ],
                "tab_index_entries": [
                    "All Issues  -:-  All issues identified",
                    "High Risk Issues  -:-  All 'High' risk issues identified",
                    "Medium Risk Issues  -:-  All 'Medium' risk issues identified",
                    "Low Risk Issues  -:-  All 'Low' risk issues identified",
                ],
                "unique_issues": [
                    {
                        "risk": "High",
                        "issue": "OpenSSL Padding Oracle (CVE-2016-2107)",
                        "impact": "Permits decryption of TLS sessions.",
                        "remediation": "Upgrade OpenSSL library.",
                        "category": "OOD",
                        "severity": 9,
                    }
                ],
                "majority_type": "ISC",
                "minority_type": "IWC",
                "majority_unique": [
                    {
                        "risk": "Medium",
                        "issue": "SMB Signing Not Required",
                        "impact": "Permits MITM attacks.",
                        "remediation": "Require SMB signing.",
                        "category": "ISC",
                        "severity": 6,
                    }
                ],
                "majority_subset": [
                    {
                        "ip": "203.0.113.10",
                        "hostnames": "edge.example.com",
                        "issue": "SMB Signing Not Required",
                        "impact": "Permits MITM attacks.",
                        "remediation": "Require SMB signing.",
                        "risk": "Medium",
                        "category": "ISC",
                        "severity": 6,
                    }
                ],
                "xlsx_filename": "external_nexpose.xlsx",
                "xlsx_base64": "UEsDBBQAAgAIACJFeGFtTmV4cG9zZQ",
            },
            "internal_nexpose_vulnerabilities": {
                "label": "Internal Nexpose Vulnerabilities",
                "high": {
                    "total_unique": 3,
                    "items": [
                        {
                            "title": "Unsupported Windows Server",
                            "impact": "Legacy operating systems permit trivial remote exploitation.",
                            "count": 5,
                        },
                        {
                            "title": "Exposed SMB Shares",
                            "impact": "Anonymous access allows data exfiltration and lateral movement.",
                            "count": 2,
                        },
                    ],
                },
                "med": {
                    "total_unique": 2,
                    "items": [
                        {
                            "title": "Outdated Database Service",
                            "impact": "Known vulnerabilities enable privilege escalation against the service.",
                            "count": 4,
                        }
                    ],
                },
                "low": {
                    "total_unique": 1,
                    "items": [
                        {
                            "title": "Information Disclosure Banner",
                            "impact": "Verbose service banners reveal version information to attackers.",
                            "count": 3,
                        }
                    ],
                },
            },
            "iot_iomt_nexpose_vulnerabilities": {
                "label": "IoT/IoMT Nexpose Vulnerabilities",
                "high": {
                    "total_unique": 2,
                    "items": [
                        {
                            "title": "Unpatched Medical Device Firmware",
                            "impact": "Outdated firmware enables arbitrary code execution on clinical systems.",
                            "count": 3,
                        }
                    ],
                },
                "med": {
                    "total_unique": 1,
                    "items": [
                        {
                            "title": "Default Credentials Enabled",
                            "impact": "Shared vendor passwords allow unauthorized access to device management.",
                            "count": 2,
                        }
                    ],
                },
                "low": {
                    "total_unique": 1,
                    "items": [
                        {
                            "title": "Deprecated TLS Protocols",
                            "impact": "Weak encryption permits interception of device telemetry.",
                            "count": 4,
                        }
                    ],
                },
            },
            "internal_nexpose_findings": {
                "findings": [
                    {
                        "Asset IP Address": "10.20.30.40",
                        "Hostname(s)": "file01.corp.example.com",
                        "Service Port": "445",
                        "Protocol": "tcp",
                        "Vulnerability Title": "SMB Signing Not Required",
                        "Impact": "Permits attackers to relay SMB authentication.",
                        "Solution": "Require SMB signing on all systems.",
                        "Category": "ISC",
                        "Details": "Signing disabled on host.",
                        "Evidence": "SMB negotiation captured.",
                        "Detailed Remediation": "Apply GPO to enforce SMB signing.",
                    }
                ],
                "software": [
                    {"Software": "Windows Server 2012 R2", "Version": "6.3.9600", "Instances": 4}
                ],
            },
            "internal_nexpose_metrics": {
                "summary": {
                    "total": 15,
                    "total_high": 6,
                    "total_med": 5,
                    "total_low": 4,
                    "unique": 8,
                    "unique_high": 3,
                    "unique_med": 3,
                    "unique_low": 2,
                    "unique_high_med": 6,
                    "total_ood": 1,
                    "total_isc": 5,
                    "total_iwc": 2,
                    "majority_count": 5,
                    "minority_count": 2,
                },
                "host_counts": [
                    {"host": "file01.corp.example.com", "high": 1, "med": 2, "low": 1},
                    {"host": "db02.corp.example.com", "high": 2, "med": 1, "low": 0},
                ],
                "top_hosts": [
                    {"host": "db02.corp.example.com", "high": 2, "med": 1, "low": 0, "total": 3, "score": 7},
                    {"host": "file01.corp.example.com", "high": 1, "med": 2, "low": 1, "total": 4, "score": 6},
                ],
                "top_hosts_high": 3,
                "top_hosts_med": 3,
                "top_hosts_low": 1,
                "top_hosts_total": 7,
                "top_impacts": [
                    {"impact": "Privilege escalation", "count": 2},
                    {"impact": "Lateral movement", "count": 2},
                ],
                "tab_index_entries": [
                    "All Issues  -:-  All issues identified",
                    "High Risk Issues  -:-  All 'High' risk issues identified",
                    "Medium Risk Issues  -:-  All 'Medium' risk issues identified",
                    "Low Risk Issues  -:-  All 'Low' risk issues identified",
                ],
                "unique_issues": [
                    {
                        "risk": "High",
                        "issue": "Unsupported Windows Server",
                        "impact": "Legacy operating systems permit trivial remote exploitation.",
                        "remediation": "Upgrade to a supported Windows Server release.",
                        "category": "OOD",
                        "severity": 9,
                    }
                ],
                "majority_type": "ISC",
                "minority_type": "IWC",
                "majority_unique": [
                    {
                        "risk": "Medium",
                        "issue": "SMB Signing Not Required",
                        "impact": "Permits MITM attacks.",
                        "remediation": "Require SMB signing.",
                        "category": "ISC",
                        "severity": 6,
                    }
                ],
                "majority_subset": [
                    {
                        "ip": "10.20.30.40",
                        "hostnames": "file01.corp.example.com",
                        "issue": "SMB Signing Not Required",
                        "impact": "Permits MITM attacks.",
                        "remediation": "Require SMB signing.",
                        "risk": "Medium",
                        "category": "ISC",
                        "severity": 6,
                    }
                ],
                "xlsx_filename": "internal_nexpose.xlsx",
                "xlsx_base64": "UEsDBBQAAgAIACJJbnRlcm5hbE5leHBvc2U",
            },
            "iot_iomt_nexpose_findings": {
                "findings": [
                    {
                        "Asset IP Address": "10.55.88.23",
                        "Hostname(s)": "mri01.med.example.com",
                        "Service Port": "80",
                        "Protocol": "tcp",
                        "Vulnerability Title": "Default Credentials Enabled",
                        "Impact": "Shared vendor passwords allow unauthorized access to device management.",
                        "Solution": "Change default credentials and enforce MFA on management portals.",
                        "Category": "ISC",
                        "Details": "Device uses manufacturer default password.",
                        "Evidence": "Successful login via vendor defaults.",
                        "Detailed Remediation": "Rotate credentials and integrate with PAM tooling.",
                    }
                ],
                "software": [
                    {"Software": "MedTech Controller", "Version": "3.2.1", "Instances": 5}
                ],
            },
            "iot_iomt_nexpose_metrics": {
                "summary": {
                    "total": 5,
                    "total_high": 2,
                    "total_med": 2,
                    "total_low": 1,
                    "unique": 3,
                    "unique_high": 1,
                    "unique_med": 1,
                    "unique_low": 1,
                    "unique_high_med": 2,
                    "total_ood": 1,
                    "total_isc": 2,
                    "total_iwc": 0,
                    "majority_count": 2,
                    "minority_count": 1,
                },
                "host_counts": [
                    {"host": "mri01.med.example.com", "high": 1, "med": 1, "low": 0},
                    {"host": "nurse01.med.example.com", "high": 0, "med": 1, "low": 1},
                ],
                "top_hosts": [
                    {"host": "mri01.med.example.com", "high": 1, "med": 1, "low": 0, "total": 2, "score": 5},
                    {"host": "nurse01.med.example.com", "high": 0, "med": 1, "low": 1, "total": 2, "score": 3},
                ],
                "top_hosts_high": 1,
                "top_hosts_med": 2,
                "top_hosts_low": 1,
                "top_hosts_total": 4,
                "top_impacts": [
                    {"impact": "Unauthorized device control", "count": 2},
                ],
                "tab_index_entries": [
                    "All Issues  -:-  All issues identified",
                    "High Risk Issues  -:-  All 'High' risk issues identified",
                    "Medium Risk Issues  -:-  All 'Medium' risk issues identified",
                    "Low Risk Issues  -:-  All 'Low' risk issues identified",
                ],
                "unique_issues": [
                    {
                        "risk": "High",
                        "issue": "Unpatched Medical Device Firmware",
                        "impact": "Outdated firmware enables arbitrary code execution on clinical systems.",
                        "remediation": "Coordinate firmware upgrades with the vendor.",
                        "category": "OOD",
                        "severity": 9,
                    }
                ],
                "majority_type": "ISC",
                "minority_type": "OOD",
                "majority_unique": [
                    {
                        "risk": "Medium",
                        "issue": "Default Credentials Enabled",
                        "impact": "Shared vendor passwords allow unauthorized access to device management.",
                        "remediation": "Rotate credentials and restrict access.",
                        "category": "ISC",
                        "severity": 6,
                    }
                ],
                "majority_subset": [
                    {
                        "ip": "10.55.88.23",
                        "hostnames": "mri01.med.example.com",
                        "issue": "Default Credentials Enabled",
                        "impact": "Shared vendor passwords allow unauthorized access to device management.",
                        "remediation": "Rotate credentials and restrict access.",
                        "risk": "Medium",
                        "category": "ISC",
                        "severity": 6,
                    }
                ],
                "xlsx_filename": "iot_nexpose.xlsx",
                "xlsx_base64": "UEsDBBQAAgAIACJJb3ROZXhwb3Nl",
            },
            "nexpose_matrix_gaps": {
                "missing_by_artifact": {
                    "external_nexpose_findings": {
                        "entries": [
                            {
                                "Vulnerability": "Legacy TLS Support",
                                "Action Required": "Confirm if TLS 1.0 can be disabled.",
                                "Remediation Impact": "May affect legacy clients.",
                                "Vulnerability Threat": "Downgrade and MITM attacks",
                                "Category": "IWC",
                                "CVE": "CVE-2021-0001",
                            }
                        ]
                    }
                }
            },
            "password": {
                "file_name": "password_dump.csv",
                "xlsx_filename": "KTOWN_Password_Report.xlsx",
                "xlsx_base64": "UEsDBBQAAgAIACJQYXNzd29yZHM",
                "raw": [
                    {
                        "Domain": "corp.example.com",
                        "Username": "svc-backup",
                        "NTLM Hash": "aad3b435b51404eeaad3b435b51404ee",
                        "NTLM Password": "Welcome1",
                        "NTLM State": "Cracked",
                        "User Info": "Backup service account",
                        "Last Changed Time": "2024-01-05",
                        "Lockout": "N",
                        "Disabled": "N",
                        "Expired": "N",
                        "No Expire": "Y",
                        "LM Hash": "",
                    },
                    {
                        "Domain": "lab.example.com",
                        "Username": "admin",
                        "NTLM Hash": "31d6cfe0d16ae931b73c59d7e0c089c0",
                        "NTLM Password": "Winter2023!",
                        "NTLM State": "Cracked",
                        "User Info": "Lab administrator",
                        "Last Changed Time": "2024-02-10",
                        "Lockout": "N",
                        "Disabled": "N",
                        "Expired": "N",
                        "No Expire": "N",
                        "LM Hash": "aad3b435b51404eeaad3b435b51404ee",
                    },
                ],
                "domains": {
                    "corp.example.com": {
                        "domain": "corp.example.com",
                        "sheets": {
                            "cracked": "cracked-corp.example.com",
                            "admin": "admin-corp.example.com",
                            "enabled": "enabled-corp.example.com",
                            "lanman": "LANMAN-corp.example.com",
                            "duplicates": "duplicates-corp.example.com",
                        },
                        "cracked": [
                            {
                                "Domain": "corp.example.com",
                                "Username": "svc-backup",
                                "NTLM Password": "Welcome1",
                                "NTLM State": "Cracked",
                            }
                        ],
                        "admin": [
                            {
                                "Domain": "corp.example.com",
                                "Username": "svc-backup",
                                "NTLM Password": "Welcome1",
                                "NTLM State": "Cracked",
                            }
                        ],
                        "enabled": [
                            {
                                "Domain": "corp.example.com",
                                "Username": "svc-helpdesk",
                                "NTLM Password": "Password123!",
                                "NTLM State": "Cracked",
                            }
                        ],
                        "lanman": [
                            {
                                "Domain": "corp.example.com",
                                "Username": "legacy",
                                "LM Hash": "aad3b435b51404eeaad3b435b51404ee",
                            }
                        ],
                        "duplicates": [
                            {"NTLM Password": "Welcome1", "Count": 6},
                            {"NTLM Password": "Password123!", "Count": 3},
                        ],
                    },
                    "lab.example.com": {
                        "domain": "lab.example.com",
                        "sheets": {
                            "cracked": "cracked-lab.example.com",
                            "admin": "admin-lab.example.com",
                            "enabled": "enabled-lab.example.com",
                            "lanman": "LANMAN-lab.example.com",
                            "duplicates": "duplicates-lab.example.com",
                        },
                        "cracked": [
                            {
                                "Domain": "lab.example.com",
                                "Username": "admin",
                                "NTLM Password": "Winter2023!",
                                "NTLM State": "Cracked",
                            }
                        ],
                        "admin": [
                            {
                                "Domain": "lab.example.com",
                                "Username": "admin",
                                "NTLM Password": "Winter2023!",
                                "NTLM State": "Cracked",
                            }
                        ],
                        "enabled": [
                            {
                                "Domain": "lab.example.com",
                                "Username": "jane",
                                "NTLM Password": "Spring2024!",
                                "NTLM State": "Cracked",
                            }
                        ],
                        "lanman": [],
                        "duplicates": [
                            {"NTLM Password": "Winter2023!", "Count": 4},
                        ],
                    },
                },
                "metrics": {
                    "corp.example.com": {
                        "domain_name": "corp.example.com",
                        "passwords_cracked": 17,
                        "admin_count": 2,
                        "lanman_stored": "Yes",
                        "enabled_accounts": 210,
                    },
                    "lab.example.com": {
                        "domain_name": "lab.example.com",
                        "passwords_cracked": 9,
                        "admin_count": 1,
                        "lanman_stored": "No",
                        "enabled_accounts": 75,
                    },
                },
            },
            "endpoint": {
                "domains": [
                    {
                        "domain": "corp.example.com",
                        "computers": [
                            {
                                "Computer": "CORP-LAP-01",
                                "Online_Status": "Online",
                                "securityproducts": [
                                    {
                                        "SecurityProduct": "Windows Defender",
                                        "Version": "4.18.230",
                                        "Status": "Enabled, UpToDate",
                                        "LastUpdated": "2024-04-15",
                                        "Running": "Yes",
                                        "VTP_Enabled": "Yes",
                                    }
                                ],
                                "usernames": ["corp\\jdoe"],
                                "ssids": ["CorpSecure"],
                            }
                        ],
                    }
                ],
                "metrics": {
                    "corp.example.com": {
                        "domain": "corp.example.com",
                        "summary": {
                            "total_computers": 25,
                            "online_count": 22,
                            "systems_ood": 3,
                            "wifi_count": 5,
                            "file_name": "corp_endpoint.csv",
                        },
                        "xlsx_filename": "endpoint_data_corp_example_com.xlsx",
                        "xlsx_base64": "UEsDBBQAAgAIACJFbmRwb2ludA",
                    }
                },
            },
        },
        "cap": {
            "firewall": {
                "firewall_cap_map": [
                    {
                        "issue": "Overly permissive inbound access",
                        "devices": "Edge-FW01",
                        "risk": "High",
                        "finding_score": 8.5,
                        "recommendation": "Review all firewall rules to ensure there is a valid business justification; document the business justification and network access requirements",
                        "score": 5,
                        "solution": "Restrict inbound rules to required services",
                    },
                    {
                        "issue": "Stale decommissioned network objects",
                        "devices": "Core-FW02",
                        "risk": "Medium",
                        "finding_score": 5.0,
                        "recommendation": "Review all firewall rules to ensure there is a valid business justification; document the business justification and network access requirements",
                        "score": 5,
                        "solution": "Remove unused objects from rule base",
                    },
                ],
            }
        },
        "extra_fields": {},
    },
    "client": {
        "id": 1,
        "contacts": [
            {
                "name": "Hank Hooper",
                "timezone": "America/Los_Angeles",
                "job_title": "CEO",
                "email": "dad@kabletown.family",
                "phone": "(212) 664-4444",
                "note": '<p>A self-described "family man," Vietnam veteran, and head of Kabletown. He always seems happy on the surface (laughing incessantly), while directing thinly-veiled insults and threats to subordinates. Handle with care.</p>',
                "note_rt": "",
            },
            {
                "name": "John Francis Donaghy",
                "timezone": "America/Los_Angeles",
                "job_title": "Vice President of East Coast Television",
                "email": "jack@nbc.com",
                "phone": "(212) 664-4444",
                "note": '<p>Prefers to go by "Jack."</p>',
                "note_rt": "",
            },
        ],
        "name": "Kabletown, Inc.",
        "short_name": "KTOWN",
        "codename": "Totally Not Comcast",
        "note": "<p>Philadelphia-based cable company Kabletown, a fictionalized depiction of the acquisition of NBC Universal by Comcast.</p>",
        "note_rt": "",
        "address": "30 Rockefeller Plaza New York City, New York 10112",
        "address_rt": "",
        "logo": "client_logos/client_logo_cover.png",
        "logo_header": "client_logos/headers/client_logo_header.png",
        "tags": ["tag1", "tag2", "tag3"],
        "extra_fields": {},
    },
    "team": [
        {
            "role": "Assessment Lead",
            "name": "Benny the Ghost",
            "email": "benny@ghostwriter.wiki",
            "start_date": "Mar. 1, 2021",
            "end_date": "Jun. 25, 2021",
            "timezone": "America/Los_Angeles",
            "phone": "(212) 664-4444",
            "note": "<p>Benny will lead the assessment for the full duration.</p>",
            "note_rt": "",
        },
        {
            "role": "Assessment Oversight",
            "name": "Christopher Maddalena",
            "email": "cmaddalena@specterops.io",
            "start_date": "Mar. 1, 2021",
            "end_date": "Jun. 25, 2021",
            "timezone": "America/Los_Angeles",
            "phone": "(212) 664-4444",
            "note": "<p>Christopher will provide oversight and assistance (as needed).</p>",
            "note_rt": "",
        },
    ],
    "objectives": [
        {
            "priority": "Primary",
            "status": "Active",
            "deadline": "Jun. 25, 2021",
            "percent_complete": 50.0,
            "tasks": [
                {
                    "deadline": "Jun. 25, 2021",
                    "marked_complete": "",
                    "task": "Extract information about Kenneth Parcell",
                    "complete": False,
                },
                {
                    "deadline": "Jun. 4, 2021",
                    "marked_complete": "Mar. 22, 2021",
                    "task": "Locate information about Kenneth Parcell to begin the search (Page Program subnet)",
                    "complete": True,
                },
            ],
            "objective": "Discover Kenneth Parcell's true identity",
            "description": '<p>It is unclear if this is a jest and part of an HR-related "flag" or a real request. The client was light on details. The objective is wide open; asking the team to find any and all information related to Kenneth Parcel, a member of NBC\'s Page Program.</p>',
            "description_rt": "",
            "result": '<p>Test result 1</p>',
            "result_rt": "",
            "complete": False,
            "marked_complete": "",
            "position": 1,
        },
        {
            "priority": "Secondary",
            "status": "Active",
            "deadline": "Jun. 25, 2021",
            "percent_complete": 0.0,
            "tasks": [
                {
                    "deadline": "Mar. 16, 2021",
                    "marked_complete": "",
                    "task": "Locate systems and data repositories used by HR and contract teams",
                    "complete": False,
                }
            ],
            "objective": "Access hosts and files containing celebrity PII",
            "description": "<p>The team may find methods of accessing data related to celebrities that appear on NBC programs. Use any discovered methods to access this information and capture evidence.</p>",
            "description_rt": "",
            "result": '<p>Test result 1</p>',
            "result_rt": "",
            "complete": False,
            "marked_complete": "",
            "position": 1,
        },
        {
            "priority": "Primary",
            "status": "Active",
            "deadline": "Apr. 23, 2021",
            "percent_complete": 0.0,
            "tasks": [
                {
                    "deadline": "Mar. 24, 2021",
                    "marked_complete": "",
                    "task": "Run BloodHound!",
                    "complete": False,
                }
            ],
            "objective": "Escalate privileges in the NBC domain to Domain Administrator or equivalent",
            "description": "<p>Active Directory is a key component of the assessment, and client is keen to learn how many attack paths may be discovered to escalate privileges within the network.</p>",
            "description_rt": "",
            "result": '<p>Test result 1</p>',
            "result_rt": "",
            "complete": False,
            "marked_complete": "",
            "position": 2,
        },
    ],
    "targets": [
        {
            "ip_address": "12.31.13.90",
            "hostname": "PP00001.NBC.LOCAL",
            "note": "<p>Computer known to be used by Kenneth Parcell. May contain celebrity PII (Parcell performs tasks for Tracy Morgan) or provide information for the Parcell objective.</p>",
            "note_rt": "",
            "compromised": False,
        }
    ],
    "scope": [
        {
            "total": 1,
            "scope": ["10.6.0.125"],
            "name": "Executive Computer",
            "description": "<p>This is Jack Donaghy's computer and should not be touched.</p>",
            "description_rt": "",
            "disallowed": True,
            "requires_caution": False,
        },
        {
            "total": 4,
            "scope": ["192.168.1.0/24", "10.100.0.0/16", "*.nbc.com", "NBC.LOCAL"],
            "name": "NBC Allowlist",
            "description": "<p>All hosts and domains in this list are allowed and related to core objectives.</p>",
            "description_rt": "",
            "disallowed": False,
            "requires_caution": False,
        },
        {
            "total": 1,
            "scope": ["12.31.13.0/24"],
            "name": "NBC Page Program",
            "description": "<p>Client advises caution while accessing this network and avoid detection. It is unclear why, but they have said it is related to the Kenneth Parcell objective.</p>",
            "description_rt": "",
            "disallowed": False,
            "requires_caution": True,
        },
    ],
    "deconflictions": [
        {
            "status": "Unrelated",
            "created_at": "2022-10-06T19:41:20.889055Z",
            "report_timestamp": "2022-10-06T19:41:20.889055Z",
            "alert_timestamp": "2022-10-06T19:41:20.889055Z",
            "response_timestamp": "2022-10-06T19:41:20.889055Z",
            "title": "A Brief Descriptive Title",
            "description": "<p>This would be a description of the alert, response, and any related assessment activity.</p>",
            "description_rt": "",
            "alert_source": "EDR",
        },
    ],
    "whitecards": [
        {
            "issued": "2022-10-13T19:18:26Z",
            "title": "Test Card",
            "description": "<p>Test description</p>",
            "description_rt": "",
        }
    ],
    "infrastructure": {
        "domains": [
            {
                "activity": "Phishing",
                "domain": "getghostwriter.io",
                "start_date": "Mar. 1, 2021",
                "end_date": "Jun. 25, 2021",
                "dns": [
                    {
                        "static_server": "172.67.132.12",
                        "transient_server": "",
                        "endpoint": "sketchy-endpoint.azureedge.net",
                        "subdomain": "code",
                    }
                ],
                "note": "<p>Domain for the first phishing campaign</p>",
                "note_rt": "",
                "extra_fields": {},
            },
            {
                "activity": "Command and Control",
                "domain": "ghostwriter.wiki",
                "start_date": "Mar. 1, 2021",
                "end_date": "Jun. 25, 2021",
                "dns": [
                    {
                        "static_server": "104.236.176.100",
                        "transient_server": "",
                        "endpoint": "",
                        "subdomain": "www",
                    }
                ],
                "note": "<p>Domain for long-haul C2 comms</p>",
                "note_rt": "",
                "extra_fields": {},
            },
            {
                "activity": "Command and Control",
                "domain": "specterops.io",
                "start_date": "Mar. 1, 2021",
                "end_date": "Jun. 25, 2021",
                "dns": [
                    {
                        "static_server": "",
                        "transient_server": "30.49.38.30",
                        "endpoint": "",
                        "subdomain": "smtp",
                    }
                ],
                "note": "<p>Domain for the short-haul C2 comms (phishing)</p>",
                "note_rt": "",
                "extra_fields": {},
            },
        ],
        "servers": [
            {
                "name": "CC-01",
                "ip_address": "104.236.176.100",
                "provider": "Digital Ocean",
                "activity": "Command and Control",
                "role": "Team Server / C2 Server",
                "start_date": "Mar. 1, 2021",
                "end_date": "Jun. 25, 2021",
                "dns": [{"domain": "ghostwriter.wiki", "endpoint": "", "subdomain": "www"}],
                "note": "<p>Long-haul C2 server</p>",
                "note_rt": "",
                "extra_fields": {},
            },
            {
                "name": "CC-02",
                "ip_address": "172.67.132.12",
                "provider": "Microsoft Azure",
                "activity": "Command and Control",
                "role": "Team Server / C2 Server",
                "start_date": "Mar. 1, 2021",
                "end_date": "Jun. 25, 2021",
                "dns": [
                    {
                        "domain": "getghostwriter.io",
                        "endpoint": "sketchy-endpoint.azureedge.net",
                        "subdomain": "code",
                    }
                ],
                "note": "<p>Short-haul C2 server for phishing</p>",
                "note_rt": "",
                "extra_fields": {},
            },
        ],
        "cloud": [
            {
                "activity": "Phishing",
                "role": "SMTP",
                "provider": "Amazon Web Services",
                "dns": [{"domain": "specterops.io", "endpoint": "", "subdomain": "smtp"}],
                "ip_address": "30.49.38.30",
                "name": "SMTP01",
                "note": "<p>SMTP server for phishing emails; running Gophish</p>",
                "note_rt": "",
            }
        ],
    },
    "severities": [
        {
            "severity": "Critical",
            "severity_color": "966FD6",
            "severity_color_rgb": [150, 111, 214],
            "severity_color_hex": ["0x96", "0x6f", "0xd6"],
            "weight": 1,
            "color": "966FD6",
            "severity_rt": "Critical",
        },
        {
            "severity": "High",
            "severity_color": "FF7E79",
            "severity_color_rgb": [255, 126, 121],
            "severity_color_hex": ["0xff", "0x7e", "0x79"],
            "weight": 2,
            "color": "FF7E79",
            "severity_rt": "High",
        },
        {
            "severity": "Medium",
            "severity_color": "F4B083",
            "severity_color_rgb": [244, 176, 131],
            "severity_color_hex": ["0xf4", "0xb0", "0x83"],
            "weight": 3,
            "color": "F4B083",
            "severity_rt": "Medium",
        },
        {
            "severity": "Low",
            "severity_color": "A8D08D",
            "severity_color_rgb": [168, 208, 141],
            "severity_color_hex": ["0xa8", "0xd0", "0x8d"],
            "weight": 4,
            "color": "A8D08D",
            "severity_rt": "Low",
        },
        {
            "severity": "Informational",
            "severity_color": "8EAADB",
            "severity_color_rgb": [142, 170, 219],
            "severity_color_hex": ["0x8e", "0xaa", "0xdb"],
            "weight": 5,
            "color": "8EAADB",
            "severity_rt": "Informational",
        },
    ],
    "findings": [
        {
            "id": 1,
            "assigned_to": "Benny the Ghost",
            "finding_type": "Network",
            "severity": "Critical",
            "severity_rt": "Critical",
            "added_as_blank": True,
            "cvss_score": "",
            "cvss_score_rt": "",
            "cvss_vector": "",
            "cvss_vector_rt": "",
            "severity_color": "966FD6",
            "severity_color_rgb": [150, 111, 214],
            "severity_color_hex": ["0x96", "0x6f", "0xd6"],
            "recommendation": "",
            "recommendation_rt": "",
            "evidence": [
                {
                    "id": 1,
                    "file_path": "evidence/2/ghost.png",
                    "url": "/media/evidence/2/ghost.png",
                    "document": "/media/evidence/2/ghost.png",
                    "friendly_name": "Ghostwriter",
                    "upload_date": "2021-03-22",
                    "caption": "Brief Caption for This Evidence",
                    "description": "",
                    "tags": ["tag1", "tag2", "tag3"],
                }
            ],
            "title": "Critical Network Finding",
            "position": 1,
            "affected_entities": "",
            "affected_entities_rt": "",
            "description": "",
            "description_rt": "",
            "impact": "",
            "impact_rt": "",
            "replication_steps": "",
            "replication_steps_rt": "",
            "host_detection_techniques": "",
            "host_detection_techniques_rt": "",
            "network_detection_techniques": "",
            "network_detection_techniques_rt": "",
            "references": "",
            "references_rt": "",
            "mitigation": "",
            "finding_guidance": "",
            "complete": False,
            "tags": ["tag1", "tag2", "tag3"],
            "extra_fields": {},
        },
    ],
    "observations": [
        {
            "id": 1,
            "title": "test observation",
            "description": "",
            "description_rt": "",
            "tags": ["tag1", "tag2", "tag3"],
            "extra_fields": {},
        }
    ],
    "docx_template": {
        "id": 1,
        "document": "/media/template_oxnfkmX.docx",
        "name": "Default Word Template",
        "doc_type": 1,
        "tags": ["tag1", "tag2", "tag3"],
    },
    "pptx_template": {
        "id": 2,
        "document": "/media/app/ghostwriter/media/templates/template.pptx",
        "name": "Default PowerPoint Template",
        "doc_type": 2,
        "tags": ["tag1", "tag2", "tag3"],
    },
    "logs": [
        {
            "entries": [
                {
                    "tags": ["tag1", "tag2", "tag3"],
                    "start_date": "2023-03-23T17:09:00Z",
                    "end_date": "2023-03-23T17:10:02Z",
                    "source_ip": "DEBIAN-DEV (192.168.85.132)",
                    "dest_ip": "",
                    "tool": "poseidon",
                    "user_context": "cmaddalena",
                    "command": "help",
                    "description": "",
                    "output": "",
                    "comments": "",
                    "operator_name": "mythic_admin",
                    "extra_fields": {},
                },
                {
                    "tags": ["tag1", "tag2", "tag3"],
                    "start_date": "2023-03-20T21:32:31Z",
                    "end_date": "2023-03-20T21:32:31Z",
                    "source_ip": "DEBIAN-DEV (192.168.85.132)",
                    "dest_ip": "",
                    "tool": "poseidon",
                    "user_context": "cmaddalena",
                    "command": "help ",
                    "description": "",
                    "output": "",
                    "comments": "",
                    "operator_name": "mythic_admin",
                    "extra_fields": {},
                },
            ],
            "name": "SpecterOps Red Team Logs",
        },
        {
            "entries": [
                {
                    "tags": ["tag1", "tag2", "tag3"],
                    "start_date": "2023-03-23T17:09:00Z",
                    "end_date": "2023-03-23T17:10:02Z",
                    "source_ip": "DEBIAN-DEV (192.168.85.132)",
                    "dest_ip": "",
                    "tool": "poseidon",
                    "user_context": "cmaddalena",
                    "command": "help",
                    "description": "",
                    "output": "",
                    "comments": "",
                    "operator_name": "mythic_admin",
                    "extra_fields": {},
                },
                {
                    "tags": ["tag1", "tag2", "tag3"],
                    "start_date": "2023-03-20T21:32:31Z",
                    "end_date": "2023-03-20T21:32:31Z",
                    "source_ip": "DEBIAN-DEV (192.168.85.132)",
                    "dest_ip": "",
                    "tool": "poseidon",
                    "user_context": "cmaddalena",
                    "command": "help ",
                    "description": "",
                    "output": "",
                    "comments": "",
                    "operator_name": "mythic_admin",
                    "extra_fields": {},
                },
            ],
            "name": "SpecterOps Red Team Log #2",
        },
    ],
    "company": {
        "name": "SpecterOps",
        "short_name": "SO",
        "address": "14 N Moore St, New York, NY 10013",
        "twitter": "@specterops",
        "email": "info@specterops.io",
    },
    "title": "Kabletown, Inc. Red Team (2021-03-01) Report",
    "complete": False,
    "archived": False,
    "delivered": False,
    "totals": {
        "objectives": 3,
        "objectives_completed": 0,
        "findings": 1,
        "findings_critical": 1,
        "findings_high": 0,
        "findings_medium": 0,
        "findings_low": 0,
        "findings_info": 0,
        "scope": 6,
        "team": 2,
        "targets": 1,
    },
    "tools": ["beacon", "covenant", "mythic", "poseidon"],
    "evidence": [
        {
            "id": 1,
            "file_path": "evidence/2/ghost.png",
            "url": "/media/evidence/2/ghost.png",
            "document": "/media/evidence/2/ghost.png",
            "friendly_name": "Ghostwriter",
            "upload_date": "2021-03-22",
            "caption": "Brief Caption for This Evidence",
            "description": "",
            "tags": ["tag1", "tag2", "tag3"],
        }
    ],
    "contacts": [
        {
            "timezone": "America/Los_Angeles",
            "name": "Test Primary Contact",
            "job_title": "Test Project Contact",
            "email": "test@example.com",
            "phone": "",
            "note": "<p>note!</p>",
            "primary": True,
        },
        {
            "timezone": "America/Los_Angeles",
            "name": "Test Secondary Contact",
            "job_title": "Test Project Contact",
            "email": "test@example.com",
            "phone": "",
            "note": "other note!",
            "primary": "",
        },
    ],
    "recipient": {
        "timezone": "America/Los_Angeles",
        "name": "Test Primary Contact",
        "job_title": "Test Project Contact",
        "email": "test@example.com",
        "phone": "",
        "note": "<p>note!</p>",
        "primary": True,
    },
    "extra_fields": {},
}


def _wrap_risk_rich_text_samples():
    """Wrap inline-only risk rich text samples with block-level markup."""

    def _wrap_risk_fields(container):
        if not isinstance(container, dict):
            return
        for key, value in list(container.items()):
            if value in (None, ""):
                continue
            if isinstance(value, dict):
                _wrap_risk_fields(value)
            if isinstance(key, str) and key.endswith("_rt"):
                container[key] = RiskScoreRangeMapping._wrap_inline_rich_text(str(value))

    _wrap_risk_fields(LINTER_CONTEXT.get("project", {}).get("risks"))

    workbook_data = LINTER_CONTEXT.get("project", {}).get("workbook_data")
    if isinstance(workbook_data, dict):
        _wrap_risk_fields(workbook_data.get("report_card"))

        grades = workbook_data.get("external_internal_grades")
        if isinstance(grades, dict):
            for category_data in grades.values():
                if not isinstance(category_data, dict):
                    continue
                _wrap_risk_fields(category_data)
                for subvalue in category_data.values():
                    if isinstance(subvalue, dict):
                        _wrap_risk_fields(subvalue)

    data_responses = LINTER_CONTEXT.get("project", {}).get("data_responses")
    if isinstance(data_responses, dict):
        _wrap_risk_fields(data_responses)


_wrap_risk_rich_text_samples()

LINTER_CONTEXT["project"]["data_artifacts"] = normalize_nexpose_artifacts_map(
    LINTER_CONTEXT["project"].get("data_artifacts", {})
)
