# Standard Libraries
import json
import logging
from datetime import date

# Django Imports
from django.conf import settings
from django.test import TestCase
from django.utils import dateformat

# 3rd Party Libraries
from rest_framework.renderers import JSONRenderer

# Ghostwriter Libraries
from ghostwriter.factories import GenerateMockProject, OplogEntryFactory, OplogFactory
from ghostwriter.modules.custom_serializers import (
    FullProjectSerializer,
    INTELLIGENCE_RESPONSE_KEYS,
    ReportDataSerializer,
)

logging.disable(logging.CRITICAL)


class ReportDataSerializerTests(TestCase):
    """Collection of tests for custom report serializer."""

    @classmethod
    def setUpTestData(cls):
        cls.num_of_contacts = 3
        cls.num_of_assignments = 3
        cls.num_of_findings = 10
        cls.num_of_scopes = 3
        cls.num_of_targets = 10
        cls.num_of_objectives = 3
        cls.num_of_subtasks = 5
        cls.num_of_domains = 6
        cls.num_of_servers = 3
        cls.num_of_deconflictions = 3

        cls.client, cls.project, cls.report = GenerateMockProject(
            cls.num_of_contacts,
            cls.num_of_assignments,
            cls.num_of_findings,
            cls.num_of_scopes,
            cls.num_of_targets,
            cls.num_of_objectives,
            cls.num_of_subtasks,
            cls.num_of_domains,
            cls.num_of_servers,
            cls.num_of_deconflictions,
        )

        # Create an object with a null value for later testing
        oplog = OplogFactory.create(project=cls.project)
        OplogEntryFactory.create(tool=None, oplog_id=oplog)

        cls.serializer = ReportDataSerializer(
            cls.report,
            exclude=[
                "id",
            ],
        )

    def setUp(self):
        pass

    def test_json_rendering(self):
        try:
            report_json = JSONRenderer().render(self.serializer.data)
            _ = json.loads(report_json)
        except Exception:
            self.fail("Failed to render report data as JSON")

    def test_expected_json_keys_exist(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        # Check expected keys are present
        self.assertTrue("report_date" in report_json)
        self.assertTrue("project" in report_json)
        self.assertTrue("client" in report_json)
        self.assertTrue("team" in report_json)
        self.assertTrue("objectives" in report_json)
        self.assertTrue("targets" in report_json)
        self.assertTrue("scope" in report_json)
        self.assertTrue("deconflictions" in report_json)
        self.assertTrue("infrastructure" in report_json)
        self.assertTrue("findings" in report_json)
        self.assertTrue("docx_template" in report_json)
        self.assertTrue("pptx_template" in report_json)
        self.assertTrue("company" in report_json)
        self.assertTrue("totals" in report_json)

    def test_extra_values(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        self.assertEqual(
            report_json["report_date"],
            dateformat.format(date.today(), settings.DATE_FORMAT),
        )

        totals = report_json["totals"]
        self.assertEqual(totals["findings"], self.num_of_findings)
        self.assertEqual(totals["targets"], self.num_of_targets)
        self.assertEqual(totals["team"], self.num_of_assignments)
        self.assertEqual(totals["objectives"], self.num_of_objectives)

        total_scope_lines = 0
        for scope in report_json["scope"]:
            total_scope_lines += scope["total"]

        self.assertEqual(totals["scope"], total_scope_lines)

        completed_objectives = 0
        for objective in report_json["objectives"]:
            if objective["complete"]:
                completed_objectives += 1

        self.assertEqual(totals["objectives_completed"], completed_objectives)

        for f in report_json["findings"]:
            self.assertTrue("ordering" in f)

    def test_values_are_not_empty(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        for key in report_json:
            self.assertTrue(report_json[key] is not None)

        for log in report_json["logs"]:
            for entry in log["entries"]:
                print(entry["tool"])
                self.assertTrue(entry["tool"] is not None)


class ProjectSerializerDataResponsesTests(TestCase):
    """Ensure project data responses are reshaped for templating."""

    @classmethod
    def setUpTestData(cls):
        cls.client, cls.project, _ = GenerateMockProject()
        cls.workbook_data = {
            "ad": {
                "domains": [
                    {
                        "domain": "corp.example.com",
                        "enabled_accounts": 220,
                        "domain_admins": 5,
                        "ent_admins": 2,
                        "exp_passwords": 12,
                        "passwords_never_exp": 8,
                        "inactive_accounts": 15,
                        "generic_accounts": 6,
                        "generic_logins": 3,
                    },
                    {
                        "domain": "lab.example.com",
                        "enabled_accounts": 80,
                        "domain_admins": 3,
                        "ent_admins": 1,
                        "exp_passwords": 5,
                        "passwords_never_exp": 2,
                        "inactive_accounts": 4,
                        "generic_accounts": 1,
                        "generic_logins": 2,
                    },
                ]
            },
            "password": {
                "policies": [
                    {
                        "domain_name": "corp.example.com",
                        "passwords_cracked": 3589,
                        "enabled_accounts": 230,
                        "admin_cracked": {"count": 2, "confirm": "yes"},
                        "lanman_stored": "yes",
                        "history": 6,
                        "max_age": 90,
                        "min_age": 0,
                        "min_length": 7,
                        "lockout_threshold": 8,
                        "lockout_duration": 15,
                        "lockout_reset": 20,
                        "complexity_enabled": "yes",
                        "fgpp": [
                            {
                                "fgpp_name": "Tier0Admins",
                                "history": 24,
                                "max_age": 0,
                                "min_age": 1,
                                "min_length": 14,
                                "lockout_threshold": 3,
                                "lockout_duration": 30,
                                "lockout_reset": 30,
                                "complexity_enabled": "no",
                            },
                            {
                                "fgpp_name": "ServiceAccounts",
                                "history": 5,
                                "max_age": 365,
                                "min_age": 0,
                                "min_length": 6,
                                "lockout_threshold": 8,
                                "lockout_duration": 10,
                                "lockout_reset": 10,
                                "complexity_enabled": "yes",
                            },
                        ],
                    },
                    {
                        "domain_name": "lab.example.com",
                        "passwords_cracked": 4875,
                        "enabled_accounts": 90,
                        "admin_cracked": {"count": 4, "confirm": "yes"},
                        "lanman_stored": "no",
                        "history": 15,
                        "max_age": 0,
                        "min_age": 2,
                        "min_length": 12,
                        "lockout_threshold": 4,
                        "lockout_duration": 0,
                        "lockout_reset": 45,
                        "complexity_enabled": "no",
                        "fgpp": {"count": 0},
                    },
                ]
            },
            "endpoint": {
                "domains": [
                    {
                        "domain": "corp.example.com",
                        "systems_ood": 25,
                        "open_wifi": 5,
                    },
                    {
                        "domain": "lab.example.com",
                        "systems_ood": 43,
                        "open_wifi": 12,
                    },
                ]
            },
            "firewall": {
                "devices": [
                    {"name": "Edge-FW01", "ood": "yes"},
                    {"name": "Core-FW02", "ood": "no"},
                ]
            },
        }

        cls.legacy_responses = {
            "cloud_config_risk": "low",
            "wireless_psk_risk": "medium",
            "system_config_risk": "medium",
            "wireless_open_risk": "high",
            "osint_squat_concern": "example.com",
            "osint_bucket_risk": "High",
            "osint_leaked_creds_risk": "Medium",
            "wireless_rogue_risk": "medium",
            "wireless_hidden_risk": "low",
            "wireless_segmentation_ssids": ["Guest"],
            "wireless_segmentation_tested": True,
            "wireless_psk_rotation_concern": "yes",
            "wireless_psk_weak_reasons": "to short and not enough entropy",
            "password_corpexamplecom_risk": "medium",
            "password_labexamplecom_risk": "high",
            "endpoint_labexamplecom_av_gap": "high",
            "endpoint_corpexamplecom_av_gap": "medium",
            "ad_corpexamplecom_domain_admins": "high",
            "ad_corpexamplecom_old_passwords": "low",
            "ad_corpexamplecom_generic_logins": "medium",
            "endpoint_labexamplecom_open_wifi": "high",
            "endpoint_corpexamplecom_open_wifi": "low",
            "ad_corpexamplecom_generic_accounts": "high",
            "ad_corpexamplecom_disabled_accounts": "high",
            "ad_corpexamplecom_enterprise_admins": "medium",
            "ad_corpexamplecom_expired_passwords": "low",
            "ad_corpexamplecom_inactive_accounts": "medium",
            "ad_corpexamplecom_passwords_never_expire": "low",
            "ad_labexamplecom_domain_admins": "medium",
            "ad_labexamplecom_enterprise_admins": "high",
            "ad_labexamplecom_expired_passwords": "medium",
            "ad_labexamplecom_passwords_never_expire": "high",
            "ad_labexamplecom_inactive_accounts": "low",
            "ad_labexamplecom_generic_accounts": "low",
            "ad_labexamplecom_generic_logins": "medium",
            "firewall_edge-fw01_type": "Next-Gen",
            "firewall_core-fw02_type": "Appliance",
        }

    def setUp(self):
        self.project = self.__class__.project
        self.project.refresh_from_db()

    def test_legacy_responses_are_restructured(self):
        self.project.workbook_data = self.workbook_data
        self.project.data_responses = self.legacy_responses
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        project_data = serializer.data["project"]
        responses = project_data["data_responses"]

        self.assertEqual(responses["cloud_config_risk"], "low")
        intelligence_summary = responses["intelligence"]
        self.assertEqual(intelligence_summary["osint_bucket_risk"], "High")
        self.assertEqual(intelligence_summary["osint_leaked_creds_risk"], "Medium")
        self.assertEqual(intelligence_summary["osint_bucket_risk_rt"], "<p>High</p>")
        self.assertEqual(
            intelligence_summary["osint_leaked_creds_risk_rt"], "<p>Medium</p>"
        )

        wireless_summary = responses["wireless"]
        self.assertEqual(wireless_summary["segmentation_ssids"], ["Guest"])
        self.assertTrue(wireless_summary["segmentation_tested"])
        self.assertEqual(wireless_summary["psk_rotation_concern"], "yes")
        self.assertEqual(wireless_summary["psk_risk"], "medium")
        self.assertEqual(wireless_summary["open_risk"], "high")
        self.assertEqual(wireless_summary["rogue_risk"], "medium")
        self.assertEqual(wireless_summary["hidden_risk"], "low")
        self.assertEqual(wireless_summary["psk_weak_reasons"], "to short and not enough entropy")
        self.assertEqual(wireless_summary["psk_risk_rt"], "<p>Medium</p>")
        self.assertEqual(wireless_summary["open_risk_rt"], "<p>High</p>")
        self.assertEqual(wireless_summary["rogue_risk_rt"], "<p>Medium</p>")
        self.assertEqual(wireless_summary["hidden_risk_rt"], "<p>Low</p>")

        ad_summary = responses["ad"]
        self.assertIn("entries", ad_summary)
        ad_entries = ad_summary["entries"]
        self.assertEqual(len(ad_entries), 2)
        corp_ad = next(entry for entry in ad_entries if entry["domain"] == "corp.example.com")
        lab_ad = next(entry for entry in ad_entries if entry["domain"] == "lab.example.com")
        self.assertEqual(corp_ad["domain_admins"], "high")
        self.assertEqual(corp_ad["inactive_accounts"], "medium")
        self.assertEqual(lab_ad["domain_admins"], "medium")
        self.assertEqual(lab_ad["enterprise_admins"], "high")
        self.assertEqual(ad_summary["domains_str"], "'corp.example.com'/'lab.example.com'")
        self.assertEqual(ad_summary["enabled_count_str"], "220/80")
        self.assertEqual(ad_summary["da_count_str"], "5/3")
        self.assertEqual(ad_summary["ea_count_str"], "2/1")
        self.assertEqual(ad_summary["ep_count_str"], "12/5")
        self.assertEqual(ad_summary["ne_count_str"], "8/2")
        self.assertEqual(ad_summary["ia_count_str"], "15/4")
        self.assertEqual(ad_summary["ga_count_str"], "6/1")
        self.assertEqual(ad_summary["gl_count_str"], "3/2")
        self.assertEqual(ad_summary["total_da_count"], 8)
        self.assertEqual(ad_summary["total_ea_count"], 3)
        self.assertEqual(ad_summary["total_ep_count"], 17)
        self.assertEqual(ad_summary["total_ne_count"], 10)
        self.assertEqual(ad_summary["total_ia_count"], 19)
        self.assertEqual(ad_summary["total_ga_count"], 7)
        self.assertEqual(ad_summary["total_gl_count"], 5)
        self.assertEqual(ad_summary["total_op_count"], 0)
        self.assertEqual(ad_summary["da_risk_string"], "High/Medium")
        self.assertEqual(ad_summary["ea_risk_string"], "Medium/High")
        self.assertEqual(ad_summary["ep_risk_string"], "Low/Medium")
        self.assertEqual(ad_summary["ne_risk_string"], "Low/High")
        self.assertEqual(ad_summary["ia_risk_string"], "Medium/Low")
        self.assertEqual(ad_summary["ga_risk_string"], "High/Low")
        self.assertEqual(ad_summary["gl_risk_string"], "Medium/Medium")
        self.assertEqual(ad_summary["da_risk_string_rt"], "<p>High/Medium</p>")
        self.assertEqual(ad_summary["ea_risk_string_rt"], "<p>Medium/High</p>")
        self.assertEqual(ad_summary["ep_risk_string_rt"], "<p>Low/Medium</p>")
        self.assertEqual(ad_summary["ne_risk_string_rt"], "<p>Low/High</p>")
        self.assertEqual(ad_summary["ia_risk_string_rt"], "<p>Medium/Low</p>")
        self.assertEqual(ad_summary["ga_risk_string_rt"], "<p>High/Low</p>")
        self.assertEqual(ad_summary["gl_risk_string_rt"], "<p>Medium/Medium</p>")

        password_summary = responses["password"]
        self.assertIn("entries", password_summary)
        password_entries = password_summary["entries"]
        self.assertEqual(len(password_entries), 2)
        corp_password = next(
            entry for entry in password_entries if entry["domain"] == "corp.example.com"
        )
        lab_password = next(
            entry for entry in password_entries if entry["domain"] == "lab.example.com"
        )
        self.assertEqual(corp_password["risk"], "medium")
        self.assertEqual(lab_password["risk"], "high")
        self.assertTrue(corp_password.get("bad_pass"))
        self.assertFalse(lab_password.get("bad_pass"))
        self.assertEqual(
            password_summary["domains_str"], "'corp.example.com'/'lab.example.com'"
        )
        self.assertEqual(password_summary["cracked_count_str"], "3589/4875")
        self.assertEqual(password_summary["cracked_risk_string"], "Medium/High")
        self.assertEqual(password_summary["cracked_risk_string_rt"], "<p>Medium/High</p>")
        self.assertEqual(password_summary["cracked_finding_string"], "3589 and 4875")
        self.assertEqual(password_summary["enabled_count_string"], "230 and 90")
        self.assertEqual(password_summary["admin_cracked_string"], "2 and 4")
        self.assertEqual(
            password_summary["admin_cracked_doms"],
            "'corp.example.com' and 'lab.example.com'",
        )
        self.assertEqual(password_summary["lanman_list_string"], "'corp.example.com'")
        self.assertEqual(password_summary["no_fgpp_string"], "'lab.example.com'")
        self.assertEqual(password_summary["bad_pass_count"], 2)
        self.assertEqual(password_summary["total_cracked"], 8464)
        self.assertEqual(
            password_summary.get("policy_cap_fields"),
            [
                "max_age",
                "min_age",
                "min_length",
                "history",
                "lockout_threshold",
                "lockout_duration",
                "lockout_reset",
                "complexity_enabled",
            ],
        )
        expected_cap_map = {
            "corp.example.com": {
                "policy": {
                    "score": 4,
                    "max_age": (
                        "Change 'Maximum Age' from 90 to == 0 to align with NIST recommendations "
                        "to not force users to arbitrarily change passwords based solely on age"
                    ),
                    "min_age": "Change 'Minimum Age' from 0 to >= 1 and < 7",
                    "min_length": "Change 'Minimum Length' from 7 to >= 8",
                    "history": "Change 'History' from 6 to >= 10",
                    "lockout_threshold": "Change 'Lockout Threshold' from 8 to > 0 and <= 6",
                    "lockout_duration": "Change 'Lockout Duration' from 15 to >= 30 or admin unlock",
                    "lockout_reset": "Change 'Lockout Reset' from 20 to >= 30",
                    "complexity_enabled": (
                        "Change 'Complexity Required' from TRUE to FALSE and implement additional password selection "
                        "controls such as blacklists"
                    ),
                },
                "fgpp": {
                    "ServiceAccounts": {
                        "score": 4,
                        "max_age": (
                            "Change 'Maximum Age' from 365 to == 0 to align with NIST recommendations "
                            "to not force users to arbitrarily change passwords based solely on age"
                        ),
                        "min_age": "Change 'Minimum Age' from 0 to >= 1 and < 7",
                        "min_length": "Change 'Minimum Length' from 6 to >= 8",
                        "history": "Change 'History' from 5 to >= 10",
                        "lockout_threshold": "Change 'Lockout Threshold' from 8 to > 0 and <= 6",
                        "lockout_duration": "Change 'Lockout Duration' from 10 to >= 30 or admin unlock",
                        "lockout_reset": "Change 'Lockout Reset' from 10 to >= 30",
                        "complexity_enabled": (
                            "Change 'Complexity Required' from TRUE to FALSE and implement additional password selection "
                            "controls such as blacklists"
                        ),
                    }
                },
            },
            "lab.example.com": {
                "policy": {
                    "score": 4,
                    "history": "Change 'History' from 15 to >= 10",
                },
            },
        }
        self.assertEqual(password_summary.get("policy_cap_map"), expected_cap_map)
        self.assertEqual(
            password_summary.get("policy_cap_context"),
            {
                "corp.example.com": {
                    "policy": {
                        "max_age": 90,
                        "min_age": 0,
                        "min_length": 7,
                        "history": 6,
                        "lockout_threshold": 8,
                        "lockout_duration": 15,
                        "lockout_reset": 20,
                        "complexity_enabled": "TRUE",
                    },
                    "fgpp": {
                        "ServiceAccounts": {
                            "max_age": 365,
                            "min_age": 0,
                            "min_length": 6,
                            "history": 5,
                            "lockout_threshold": 8,
                            "lockout_duration": 10,
                            "lockout_reset": 10,
                            "complexity_enabled": "TRUE",
                        }
                    },
                },
                "lab.example.com": {
                    "policy": {
                        "history": 15,
                    }
                },
            },
        )
        self.assertEqual(
            corp_password.get("bad_policy_fields"),
            [
                "max_age",
                "min_age",
                "min_length",
                "history",
                "lockout_threshold",
                "lockout_duration",
                "lockout_reset",
                "complexity_enabled",
            ],
        )
        self.assertIn("policy_cap_values", corp_password)
        self.assertIn("fgpp_bad_fields", corp_password)
        self.assertIn("fgpp_cap_values", corp_password)
        self.assertIsNone(lab_password.get("bad_policy_fields"))

        endpoint_summary = responses["endpoint"]
        self.assertIn("entries", endpoint_summary)
        endpoint_entries = endpoint_summary["entries"]
        self.assertEqual(len(endpoint_entries), 2)
        corp_endpoint = next(entry for entry in endpoint_entries if entry["domain"] == "corp.example.com")
        lab_endpoint = next(entry for entry in endpoint_entries if entry["domain"] == "lab.example.com")
        self.assertEqual(corp_endpoint["av_gap"], "medium")
        self.assertEqual(corp_endpoint["open_wifi"], "low")
        self.assertEqual(lab_endpoint["av_gap"], "high")
        self.assertEqual(lab_endpoint["open_wifi"], "high")
        self.assertNotIn(
            "corpexamplecom", [entry["domain"] for entry in endpoint_entries]
        )
        self.assertNotIn(
            "labexamplecom", [entry["domain"] for entry in endpoint_entries]
        )
        self.assertEqual(endpoint_summary["domains_str"], "corp.example.com/lab.example.com")
        self.assertEqual(endpoint_summary["ood_count_str"], "25/43")
        self.assertEqual(endpoint_summary["wifi_count_str"], "5/12")
        self.assertEqual(endpoint_summary["ood_risk_string"], "Medium/High")
        self.assertEqual(endpoint_summary["wifi_risk_string"], "Low/High")
        self.assertEqual(endpoint_summary["ood_risk_string_rt"], "<p>Medium/High</p>")
        self.assertEqual(endpoint_summary["wifi_risk_string_rt"], "<p>Low/High</p>")

        firewall_summary = responses["firewall"]
        self.assertIn("entries", firewall_summary)
        firewall_entries = firewall_summary["entries"]
        self.assertEqual(len(firewall_entries), 2)
        edge_firewall = next(entry for entry in firewall_entries if entry["name"] == "Edge-FW01")
        core_firewall = next(entry for entry in firewall_entries if entry["name"] == "Core-FW02")
        self.assertEqual(edge_firewall["type"], "Next-Gen")
        self.assertEqual(core_firewall["type"], "Appliance")
        self.assertEqual(firewall_summary["ood_name_list"], "'Edge-FW01'")
        self.assertEqual(firewall_summary["ood_count"], 1)

        self.assertNotIn("password_corpexamplecom_risk", responses)
        self.assertNotIn("endpoint_corpexamplecom_av_gap", responses)
        self.assertNotIn("firewall_edge-fw01_type", responses)

    def test_dns_zone_transfer_summary_is_exposed(self):
        workbook_payload = {
            "dns": {
                "records": [
                    {"zone_transfer": "yes"},
                    {"zone_transfer": "no"},
                    {"zone_transfer": "YES"},
                ]
            }
        }

        self.project.workbook_data = workbook_payload
        self.project.data_responses = {"dns": {"existing": "value"}}
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        dns_summary = responses.get("dns")
        self.assertIsInstance(dns_summary, dict)
        self.assertEqual(dns_summary.get("zone_trans"), 2)
        self.assertEqual(dns_summary.get("existing"), "value")

    def test_dns_unique_soa_fields_collated_from_entries(self):
        stored_responses = {
            "dns": {
                "entries": [
                    {"domain": "one.example", "soa_fields": ["serial", "refresh", "serial"]},
                    {"domain": "two.example", "soa_fields": ["retry", " refresh ", None]},
                    {"domain": "three.example", "soa_fields": "invalid"},
                    "not-a-dict",
                ]
            }
        }

        self.project.data_responses = stored_responses
        self.project.workbook_data = {}
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        dns_summary = responses.get("dns")
        self.assertIsInstance(dns_summary, dict)
        self.assertEqual(
            dns_summary.get("unique_soa_fields"),
            ["serial", "refresh", "retry"],
        )
        self.assertEqual(
            dns_summary.get("soa_field_cap_map"),
            {
                "serial": "Update to match the 'YYYYMMDDnn' scheme",
                "refresh": "Update to a value between 1200 and 43200 seconds",
                "retry": "Update to a value less than or equal to half the REFRESH",
            },
        )

    def test_workbook_ad_metrics_are_exposed_without_legacy_entries(self):
        workbook_payload = {
            "ad": {
                "domains": [
                    {
                        "domain": "legacy.local",
                        "functionality_level": "Windows 2000 Mixed",
                        "total_accounts": 200,
                        "enabled_accounts": 150,
                        "old_passwords": 40,
                        "inactive_accounts": 35,
                        "domain_admins": 12,
                        "ent_admins": 6,
                        "exp_passwords": 22,
                        "passwords_never_exp": 14,
                        "generic_accounts": 9,
                        "generic_logins": 4,
                    },
                    {
                        "domain": "modern.local",
                        "functionality_level": "Windows Server 2016",
                        "total_accounts": 100,
                        "enabled_accounts": 95,
                        "old_passwords": 5,
                        "inactive_accounts": 8,
                        "domain_admins": 4,
                        "ent_admins": 1,
                        "exp_passwords": 8,
                        "passwords_never_exp": 6,
                        "generic_accounts": 2,
                        "generic_logins": 1,
                    },
                    {
                        "domain": "ancient.local",
                        "functionality_level": "Windows 2003 Native",
                        "total_accounts": 80,
                        "enabled_accounts": 60,
                        "old_passwords": 18,
                        "inactive_accounts": 12,
                        "domain_admins": 7,
                        "ent_admins": 3,
                        "exp_passwords": 11,
                        "passwords_never_exp": 9,
                        "generic_accounts": 5,
                        "generic_logins": 2,
                    },
                ]
            }
        }

        self.project.data_responses = {}
        self.project.workbook_data = workbook_payload
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]
        ad_summary = responses.get("ad")

        self.assertIsInstance(ad_summary, dict)
        self.assertEqual(ad_summary.get("old_domains_string"), "'legacy.local' and 'ancient.local'")
        self.assertEqual(ad_summary.get("old_domains_str"), "'legacy.local'/'ancient.local'")
        self.assertEqual(ad_summary.get("old_domains_count"), 2)
        self.assertEqual(ad_summary.get("risk_contrib"), [])
        self.assertEqual(
            ad_summary.get("domain_metrics"),
            [
                {
                    "domain_name": "legacy.local",
                    "disabled_count": 50,
                    "disabled_pct": 25.0,
                    "old_pass_pct": 26.7,
                    "ia_pct": 23.3,
                },
                {
                    "domain_name": "modern.local",
                    "disabled_count": 5,
                    "disabled_pct": 5.0,
                    "old_pass_pct": 5.3,
                    "ia_pct": 8.4,
                },
                {
                    "domain_name": "ancient.local",
                    "disabled_count": 20,
                    "disabled_pct": 25.0,
                    "old_pass_pct": 30.0,
                    "ia_pct": 20.0,
                },
            ],
        )
        self.assertEqual(ad_summary.get("disabled_account_string"), "50, 5 and 20")
        self.assertEqual(ad_summary.get("disabled_account_pct_string"), "25%, 5% and 25%")
        self.assertEqual(ad_summary.get("old_password_string"), "40, 5 and 18")
        self.assertEqual(ad_summary.get("old_password_pct_string"), "26.7%, 5.3% and 30%")
        self.assertEqual(ad_summary.get("inactive_accounts_string"), "35, 8 and 12")
        self.assertEqual(ad_summary.get("inactive_accounts_pct_string"), "23.3%, 8.4% and 20%")
        self.assertEqual(ad_summary.get("domain_admins_string"), "12, 4 and 7")
        self.assertEqual(ad_summary.get("ent_admins_string"), "6, 1 and 3")
        self.assertEqual(ad_summary.get("exp_passwords_string"), "22, 8 and 11")
        self.assertEqual(ad_summary.get("never_expire_string"), "14, 6 and 9")
        self.assertEqual(ad_summary.get("generic_accounts_string"), "9, 2 and 5")
        self.assertEqual(ad_summary.get("generic_logins_string"), "4, 1 and 2")
        self.assertEqual(ad_summary.get("total_da_count"), 23)
        self.assertEqual(ad_summary.get("total_ea_count"), 10)
        self.assertEqual(ad_summary.get("total_ep_count"), 41)
        self.assertEqual(ad_summary.get("total_ne_count"), 29)
        self.assertEqual(ad_summary.get("total_ia_count"), 55)
        self.assertEqual(ad_summary.get("total_ga_count"), 16)
        self.assertEqual(ad_summary.get("total_gl_count"), 7)
        self.assertEqual(ad_summary.get("total_op_count"), 63)

    def test_ad_summary_includes_default_old_domain_count(self):
        workbook_payload = {
            "ad": {
                "domains": [
                    {
                        "domain": "modern.local",
                        "functionality_level": "Windows Server 2016",
                        "total_accounts": 100,
                        "enabled_accounts": 90,
                        "old_passwords": 10,
                        "inactive_accounts": 8,
                    }
                ]
            }
        }

        self.project.data_responses = {}
        self.project.workbook_data = workbook_payload
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"].get("data_responses")
        ad_summary = responses.get("ad") if isinstance(responses, dict) else None

        self.assertIsInstance(ad_summary, dict)
        self.assertNotIn("old_domains_string", ad_summary)
        self.assertIsNone(ad_summary.get("old_domains_str"))
        self.assertEqual(ad_summary.get("old_domains_count"), 0)
        self.assertEqual(ad_summary.get("risk_contrib"), [])
        self.assertEqual(ad_summary.get("total_da_count"), 0)
        self.assertEqual(ad_summary.get("total_ea_count"), 0)
        self.assertEqual(ad_summary.get("total_ep_count"), 0)
        self.assertEqual(ad_summary.get("total_ne_count"), 0)
        self.assertEqual(ad_summary.get("total_ia_count"), 8)
        self.assertEqual(ad_summary.get("total_ga_count"), 0)
        self.assertEqual(ad_summary.get("total_gl_count"), 0)
        self.assertEqual(ad_summary.get("total_op_count"), 10)

    def test_ad_summary_populates_risk_contrib_from_entries(self):
        workbook_payload = {
            "external_internal_grades": {
                "internal": {"iam": {"risk": "Medium"}},
            },
            "ad": {
                "domains": [
                    {
                        "domain": "legacy.local",
                        "functionality_level": "Windows Server 2016",
                        "total_accounts": 120,
                        "enabled_accounts": 90,
                        "old_passwords": 12,
                        "inactive_accounts": 8,
                        "domain_admins": 6,
                        "ent_admins": 2,
                        "exp_passwords": 10,
                        "passwords_never_exp": 5,
                        "generic_accounts": 4,
                        "generic_logins": 2,
                    }
                ]
            },
        }

        stored_responses = {
            "ad": {
                "entries": [
                    {
                        "domain": "legacy.local",
                        "domain_admins": "medium",
                        "enterprise_admins": "low",
                        "expired_passwords": "high",
                        "passwords_never_expire": "medium",
                        "inactive_accounts": "medium",
                        "generic_accounts": "high",
                        "generic_logins": "medium",
                        "old_passwords": "low",
                        "disabled_accounts": "medium",
                    }
                ]
            }
        }

        self.project.workbook_data = workbook_payload
        self.project.data_responses = stored_responses
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]
        ad_summary = responses.get("ad")

        self.assertEqual(
            ad_summary.get("risk_contrib"),
            [
                "the number of Domain Admin accounts",
                "the number of accounts with expired passwords",
                "the number of accounts set with passwords that never expire",
                "the number of potentially inactive accounts",
                "the number of potentially generic accounts",
                "the number of generic accounts logged into systems",
                "the number of disabled accounts",
            ],
        )

    def test_new_structure_is_preserved(self):
        structured = {
            "cloud_config_risk": "low",
            "osint_bucket_risk": "High",
            "osint_leaked_creds_risk": "Medium",
            "ad": [{"domain": "corp.example.com", "domain_admins": "medium"}],
            "password": {
                "entries": [{"domain": "corp.example.com", "risk": "low"}],
                "domains_str": "'corp.example.com'",
                "cracked_count_str": "100",
                "cracked_risk_string": "Low",
                "total_cracked": 0,
            },
            "endpoint": {
                "entries": [
                    {"domain": "corp.example.com", "av_gap": "medium", "open_wifi": "low"},
                ],
                "domains_str": "corp.example.com",
                "ood_count_str": "25",
                "wifi_count_str": "5",
                "ood_risk_string": "medium",
                "wifi_risk_string": "low",
            },
            "firewall": [
                {"name": "Edge-FW01", "type": "Next-Gen"},
            ],
        }

        self.project.workbook_data = self.workbook_data
        self.project.data_responses = structured
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        for key, value in structured.items():
            self.assertIn(key, responses)
            self.assertEqual(responses[key], value)

        self.assertIn("endpoint", responses)
        self.assertIn("intelligence", responses)

    def test_intelligence_section_defaults_present(self):
        self.project.data_responses = {}
        self.project.workbook_data = {
            "osint": {
                "total_squat": 0,
                "total_buckets": 0,
                "total_leaks": 0,
            }
        }
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        intelligence_section = responses.get("intelligence")
        self.assertIsInstance(intelligence_section, dict)
        for key in INTELLIGENCE_RESPONSE_KEYS:
            self.assertIn(key, intelligence_section)
            self.assertIsNone(intelligence_section[key])

    def test_standard_sections_are_always_present(self):
        self.project.data_responses = {}
        self.project.workbook_data = {}
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        expected_sections = [
            "general",
            "intelligence",
            "iot_iomt",
            "overall_risk",
            "ad",
            "password",
            "endpoint",
            "firewall",
            "dns",
            "wireless",
        ]

        for section in expected_sections:
            self.assertIn(section, responses)
            self.assertIsInstance(responses[section], dict)

        intelligence_section = responses["intelligence"]
        for key in INTELLIGENCE_RESPONSE_KEYS:
            self.assertIn(key, intelligence_section)
            self.assertIsNone(intelligence_section[key])

        self.assertEqual(responses["iot_iomt"].get("iot_testing_confirm"), "no")
        self.assertEqual(responses["endpoint"].get("entries"), [])
        self.assertEqual(responses["ad"].get("entries"), [])
        self.assertEqual(responses["firewall"].get("entries"), [])

        password_section = responses["password"]
        self.assertEqual(password_section.get("entries"), [])
        self.assertEqual(password_section.get("bad_pass_count"), 0)
        self.assertEqual(password_section.get("total_cracked"), 0)

    def test_iot_testing_confirm_defaults_to_no(self):
        self.project.data_responses = {}
        self.project.workbook_data = {}
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        self.assertIn("iot_iomt", responses)
        self.assertEqual(responses["iot_iomt"].get("iot_testing_confirm"), "no")

    def test_iot_testing_confirm_reflects_yes_response(self):
        self.project.data_responses = {"iot_testing_confirm": "yes"}
        self.project.workbook_data = {}
        self.project.save(update_fields=["workbook_data", "data_responses"])

        serializer = FullProjectSerializer(self.project)
        responses = serializer.data["project"]["data_responses"]

        self.assertEqual(responses["iot_iomt"].get("iot_testing_confirm"), "yes")
