"""Unit tests for workbook helper utilities."""

# Django Imports
from django import forms
from django.test import SimpleTestCase

# Ghostwriter Libraries
from ghostwriter.rolodex.forms_workbook import ProjectDataResponsesForm, SummaryMultipleChoiceField
from ghostwriter.rolodex.views import _build_grouped_data_responses
from ghostwriter.rolodex.workbook import (
    DNS_SOA_FIELD_CHOICES,
    SCOPE_CHOICES,
    WEAK_PSK_SUMMARY_MAP,
    YES_NO_CHOICES,
    build_data_configuration,
    build_scope_summary,
    build_workbook_sections,
    normalize_scope_selection,
    prepare_data_responses_initial,
)
from ghostwriter.rolodex.workbook_entry import build_workbook_entry_payload
from ghostwriter.rolodex.workbook_defaults import (
    ensure_data_responses_defaults,
    normalize_workbook_payload,
)


class WorkbookHelpersTests(SimpleTestCase):
    """Validate workbook summary helpers."""

    def test_build_workbook_sections_returns_structured_output(self):
        workbook_data = {
            "client": {"name": "Example", "total": 3},
            "report_card": {"overall": "A"},
        }

        sections = build_workbook_sections(workbook_data)

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["key"], "client")
        self.assertEqual(sections[0]["title"], "Client")
        self.assertEqual(sections[0]["slug"], "workbook-client")
        self.assertEqual(sections[0]["script_id"], "workbook-section-data-workbook-client")
        self.assertEqual(sections[0]["data"], {"name": "Example"})
        self.assertEqual(sections[0]["tree"]["type"], "dict")
        self.assertEqual(sections[0]["tree"]["items"][0]["label"], "Name")
        self.assertEqual(sections[0]["tree"]["items"][0]["value"]["type"], "value")
        items = sections[0]["tree"]["items"]
        self.assertEqual(items[0]["value"]["display"], "Example")
        self.assertEqual(items[1]["label"], "Total")
        self.assertEqual(items[1]["value"]["display"], "3")

    def test_non_mapping_returns_empty_sections(self):
        self.assertEqual(build_workbook_sections(None), [])
        self.assertEqual(build_workbook_sections([]), [])

    def test_sections_follow_display_order(self):
        workbook_data = {
            "wireless": {},
            "client": {},
            "general": {},
        }

        sections = build_workbook_sections(workbook_data)

        ordered_keys = [section["key"] for section in sections]
        self.assertEqual(ordered_keys[:3], ["client", "general", "wireless"])

    def test_build_workbook_sections_hides_generated_sections(self):
        normalized = normalize_workbook_payload(
            {"general": {"external_start": "2025-01-10"}}
        )

        sections = build_workbook_sections(normalized)
        keys = [section["key"] for section in sections]

        self.assertEqual(keys, ["general"])
        self.assertNotIn("endpoint", keys)

    def test_required_files_include_slug(self):
        workbook_data = {
            "dns": {"records": [{"domain": "example.com"}]},
        }

        _, required_files = build_data_configuration(workbook_data)

        self.assertTrue(required_files)
        self.assertIn("slug", required_files[0])
        self.assertEqual(required_files[0]["slug"], "required_dns-report-csv_example-com")

    def test_scope_question_added_with_defaults(self):
        questions, _ = build_data_configuration({}, project_type="Gold")

        self.assertGreaterEqual(len(questions), 2)
        scope_question = questions[0]
        self.assertEqual(scope_question["key"], "assessment_scope")
        self.assertEqual(scope_question["field_kwargs"].get("choices"), SCOPE_CHOICES)
        self.assertEqual(
            scope_question["field_kwargs"].get("initial"),
            ["external", "internal", "firewall"],
        )

        followup = next((q for q in questions if q["key"] == "assessment_scope_cloud_on_prem"), None)
        self.assertIsNotNone(followup)
        assert followup is not None  # pragma: no cover - typing aid
        self.assertEqual(followup["field_kwargs"].get("choices"), YES_NO_CHOICES)

    def test_prepare_data_responses_initial_applies_scope_defaults(self):
        normalized = prepare_data_responses_initial({}, project_type="Silver")

        general = normalized.get("general")
        self.assertIsInstance(general, dict)
        assert isinstance(general, dict)  # pragma: no cover - typing hint
        self.assertEqual(general.get("assessment_scope"), ["external", "firewall"])

    def test_prepare_data_responses_initial_preserves_existing_scope(self):
        normalized = prepare_data_responses_initial(
            {"general": {"assessment_scope": ["cloud"]}},
            project_type="Gold",
        )

        general = normalized.get("general")
        self.assertIsInstance(general, dict)
        assert isinstance(general, dict)  # pragma: no cover - typing hint
        self.assertEqual(general.get("assessment_scope"), ["cloud"])

    def test_nexpose_requirements_added_for_positive_totals(self):
        workbook_data = {
            "external_nexpose": {"total": 1},
            "internal_nexpose": {"total": 2},
            "iot_iomt_nexpose": {"total": 4},
        }

        _, required_files = build_data_configuration(workbook_data)

        labels = {entry["label"] for entry in required_files}
        self.assertIn("external_nexpose_xml.xml", labels)
        self.assertIn("internal_nexpose_xml.xml", labels)
        self.assertIn("iot_nexpose_xml.xml", labels)

    def test_iot_testing_question_added_by_default(self):
        questions, _ = build_data_configuration({})

        iot_question = next(
            (q for q in questions if q["key"] == "iot_testing_confirm"),
            None,
        )

        self.assertIsNotNone(iot_question)
        assert iot_question is not None  # pragma: no cover - clarify typing
        self.assertEqual(iot_question["label"], "Was Internal IoT/IoMT testing performed?")
        self.assertEqual(iot_question["section"], "IoT/IoMT")
        self.assertEqual(iot_question["field_kwargs"].get("choices"), YES_NO_CHOICES)
        self.assertEqual(iot_question["field_kwargs"].get("initial"), "no")

    def test_dns_soa_question_added_when_issue_present(self):
        data_artifacts = {
            "dns_issues": [
                {
                    "domain": "example.com",
                    "issues": [
                        {
                            "issue": "One or more SOA fields are outside recommended ranges",
                        }
                    ],
                }
            ]
        }

        questions, _ = build_data_configuration({}, data_artifacts=data_artifacts)

        dns_question = next(
            (q for q in questions if q["key"] == "dns_example-com_soa_fields"),
            None,
        )

        self.assertIsNotNone(dns_question)
        assert dns_question is not None  # pragma: no cover - clarify typing
        self.assertEqual(dns_question["section"], "DNS")
        self.assertEqual(dns_question["subheading"], "example.com")
        self.assertEqual(dns_question["field_kwargs"].get("choices"), DNS_SOA_FIELD_CHOICES)

    def test_nexpose_requirements_skip_zero_totals(self):
        workbook_data = {
            "external_nexpose": {"total": 0},
            "internal_nexpose": {"total": 0},
            "iot_iomt_nexpose": {"total": 0},
        }

        _, required_files = build_data_configuration(workbook_data)

        labels = {entry["label"] for entry in required_files}
        self.assertNotIn("external_nexpose_xml.xml", labels)
        self.assertNotIn("internal_nexpose_xml.xml", labels)
        self.assertNotIn("iot_nexpose_xml.xml", labels)

    def test_firewall_requirement_included_when_unique_values_present(self):
        workbook_data = {
            "firewall": {"unique": 2},
        }

        _, required_files = build_data_configuration(workbook_data)

        labels = [entry["label"] for entry in required_files]
        self.assertIn("firewall_xml.xml", labels)

    def test_firewall_device_questions_include_type_field(self):
        workbook_data = {
            "firewall": {
                "devices": [
                    {"name": "FW-1"},
                    {"name": "Branch"},
                    "Unnamed Entry",
                ]
            }
        }

        questions, _ = build_data_configuration(workbook_data)

        firewall_questions = [q for q in questions if q["section"] == "Firewall"]
        self.assertEqual(len(firewall_questions), 3)
        first_question = firewall_questions[0]
        self.assertEqual(first_question["label"], "Firewall Type")
        self.assertEqual(first_question["subheading"], "FW-1")
        self.assertTrue(first_question["key"].startswith("firewall_"))
        self.assertTrue(first_question["key"].endswith("_type"))
        last_question = firewall_questions[-1]
        self.assertEqual(last_question["subheading"], "Unnamed Entry")

    def test_osint_risk_questions_added_when_counts_present(self):
        workbook_data = {
            "osint": {
                "total_squat": 1,
                "total_buckets": 2,
                "total_leaks": 3,
            }
        }

        questions, _ = build_data_configuration(workbook_data)

        intelligence_questions = [q for q in questions if q["section"] == "Intelligence"]
        keys = {question["key"] for question in intelligence_questions}

        self.assertIn("osint_squat_concern", keys)
        self.assertIn("osint_bucket_risk", keys)
        self.assertIn("osint_leaked_creds_risk", keys)

        bucket_question = next(q for q in intelligence_questions if q["key"] == "osint_bucket_risk")
        self.assertEqual(bucket_question["label"], "What is the risk you would assign to the exposed buckets found?")
        self.assertEqual(
            bucket_question["field_kwargs"]["choices"],
            (("High", "High"), ("Medium", "Medium"), ("Low", "Low")),
        )

    def test_sections_skipped_when_workbook_data_missing(self):
        normalized = normalize_workbook_payload({"general": {"external_start": "2025-01-10"}})

        questions, _ = build_data_configuration(normalized)
        sections = {question["section"] for question in questions}

        self.assertNotIn("Wireless", sections)
        self.assertNotIn("Password Policies", sections)
        self.assertNotIn("Active Directory", sections)

    def test_password_questions_skipped_for_empty_policies(self):
        normalized = normalize_workbook_payload({"password": {"policies": []}})

        questions, _ = build_data_configuration(normalized)
        sections = {question["section"] for question in questions}

        self.assertNotIn("Password Policies", sections)

    def test_normalize_workbook_payload_populates_expected_defaults(self):
        normalized = normalize_workbook_payload({})

        self.assertIn("endpoint", normalized)
        self.assertEqual(normalized["endpoint"]["domains"], [])
        self.assertIn("password", normalized)
        self.assertEqual(normalized["password"]["policies"], [])
        meta = normalized.get("__meta__", {})
        uploaded = meta.get("uploaded_sections")
        self.assertIsInstance(uploaded, list)
        self.assertEqual(uploaded, [])

    def test_ensure_data_responses_defaults_populates_structure(self):
        defaults = ensure_data_responses_defaults({})

        self.assertIn("general", defaults)
        self.assertEqual(defaults["general"]["assessment_scope"], [])
        self.assertIn("password", defaults)
        self.assertIn("hashes_obtained", defaults["password"])
        self.assertIsNone(defaults["password"]["hashes_obtained"])
        self.assertEqual(defaults["password"]["entries"], [])
        self.assertEqual(defaults["firewall"].get("ood_count"), 0)
        self.assertEqual(defaults["firewall"].get("ood_name_list"), "")
        self.assertIn("wireless", defaults)
        self.assertIn("overall_risk", defaults)

    def test_wireless_psk_questions_include_summary_and_networks(self):
        workbook_data = {"wireless": {"weak_psks": "yes"}}

        questions, _ = build_data_configuration(workbook_data)

        keys = {question["key"] for question in questions}
        self.assertIn("wireless_psk_weak_reasons", keys)
        self.assertIn("wireless_psk_masterpass", keys)
        self.assertIn("wireless_psk_masterpass_ssids", keys)

        weak_reason = next(q for q in questions if q["key"] == "wireless_psk_weak_reasons")
        self.assertIs(weak_reason["field_class"], SummaryMultipleChoiceField)
        self.assertEqual(weak_reason["field_kwargs"].get("summary_map"), WEAK_PSK_SUMMARY_MAP)

    def test_scope_summary_generation(self):
        summary = build_scope_summary(["external", "internal", "firewall"], None)
        self.assertEqual(
            summary,
            "External network and systems, Internal network and systems and Firewall configuration(s) & rules",
        )

        cloud_on_prem = build_scope_summary(["external", "cloud"], "yes")
        self.assertEqual(
            cloud_on_prem,
            "External network and systems, Cloud/On-Prem network and systems and Cloud management configuration",
        )

        cloud_only = build_scope_summary(["external", "cloud"], "no")
        self.assertEqual(
            cloud_only,
            "External network and systems, Cloud systems and Cloud management configuration",
        )

    def test_scope_selection_normalization(self):
        ordered = normalize_scope_selection(["cloud", "external", "wireless"])
        self.assertEqual(ordered, ["external", "wireless", "cloud"])
        self.assertEqual(normalize_scope_selection("internal"), ["internal"])


class ProjectDataResponsesFormTests(SimpleTestCase):
    """Ensure workbook form helpers preserve existing grouped responses."""

    def test_existing_endpoint_entries_preserve_initial_values(self):
        questions = [
            {
                "key": "endpoint_corpexamplecom_av_gap",
                "label": "Endpoint AV Gap",
                "section": "Endpoint",
                "section_key": "endpoint",
                "subheading": "corp.example.com",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "label": "Endpoint AV Gap",
                    "required": False,
                    "choices": (("low", "Low"), ("medium", "Medium"), ("high", "High")),
                },
                "entry_slug": "endpoint_corpexamplecom",
                "entry_field_key": "av_gap",
            },
            {
                "key": "endpoint_corpexamplecom_open_wifi",
                "label": "Endpoint Open WiFi",
                "section": "Endpoint",
                "section_key": "endpoint",
                "subheading": "corp.example.com",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "label": "Endpoint Open WiFi",
                    "required": False,
                    "choices": (("low", "Low"), ("medium", "Medium"), ("high", "High")),
                },
                "entry_slug": "endpoint_corpexamplecom",
                "entry_field_key": "open_wifi",
            },
            {
                "key": "endpoint_labexamplecom_av_gap",
                "label": "Endpoint AV Gap",
                "section": "Endpoint",
                "section_key": "endpoint",
                "subheading": "lab.example.com",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "label": "Endpoint AV Gap",
                    "required": False,
                    "choices": (("low", "Low"), ("medium", "Medium"), ("high", "High")),
                },
                "entry_slug": "endpoint_labexamplecom",
                "entry_field_key": "av_gap",
            },
            {
                "key": "endpoint_labexamplecom_open_wifi",
                "label": "Endpoint Open WiFi",
                "section": "Endpoint",
                "section_key": "endpoint",
                "subheading": "lab.example.com",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "label": "Endpoint Open WiFi",
                    "required": False,
                    "choices": (("low", "Low"), ("medium", "Medium"), ("high", "High")),
                },
                "entry_slug": "endpoint_labexamplecom",
                "entry_field_key": "open_wifi",
            },
        ]

        initial = {
            "endpoint": {
                "entries": [
                    {
                        "domain": "corp.example.com",
                        "av_gap": "medium",
                        "open_wifi": "low",
                    },
                    {
                        "domain": "lab.example.com",
                        "av_gap": "high",
                        "open_wifi": "high",
                    },
                ],
                "domains_str": "corp.example.com/lab.example.com",
            }
        }

        form = ProjectDataResponsesForm(question_definitions=questions, initial=initial)

        self.assertEqual(form.fields["endpoint_corpexamplecom_av_gap"].initial, "medium")
        self.assertEqual(form.fields["endpoint_corpexamplecom_open_wifi"].initial, "low")
        self.assertEqual(form.fields["endpoint_labexamplecom_av_gap"].initial, "high")
        self.assertEqual(form.fields["endpoint_labexamplecom_open_wifi"].initial, "high")

    def test_existing_firewall_entries_preserve_initial_values(self):
        questions = [
            {
                "key": "firewall_edge-fw01_type",
                "label": "Firewall Type",
                "section": "Firewall",
                "section_key": "firewall",
                "subheading": "Edge-FW01",
                "field_class": forms.CharField,
                "field_kwargs": {
                    "label": "Firewall Type",
                    "required": False,
                },
                "entry_slug": "firewall_edge-fw01",
                "entry_field_key": "type",
            }
        ]

        initial = {
            "firewall": {
                "entries": [
                    {
                        "name": "Edge-FW01",
                        "type": "Next-Gen",
                    }
                ]
            }
        }

        form = ProjectDataResponsesForm(question_definitions=questions, initial=initial)

        self.assertEqual(form.fields["firewall_edge-fw01_type"].initial, "Next-Gen")


class BuildGroupedDataResponsesTests(SimpleTestCase):
    """Validate grouped response normalization preserves summaries."""

    def test_existing_endpoint_summary_preserved(self):
        questions = [
            {
                "key": "endpoint_corpexamplecom_av_gap",
                "section_key": "endpoint",
                "subheading": "corp.example.com",
                "entry_slug": "endpoint_corpexamplecom",
                "entry_field_key": "av_gap",
            },
            {
                "key": "endpoint_corpexamplecom_open_wifi",
                "section_key": "endpoint",
                "subheading": "corp.example.com",
                "entry_slug": "endpoint_corpexamplecom",
                "entry_field_key": "open_wifi",
            },
            {
                "key": "endpoint_labexamplecom_av_gap",
                "section_key": "endpoint",
                "subheading": "lab.example.com",
                "entry_slug": "endpoint_labexamplecom",
                "entry_field_key": "av_gap",
            },
            {
                "key": "endpoint_labexamplecom_open_wifi",
                "section_key": "endpoint",
                "subheading": "lab.example.com",
                "entry_slug": "endpoint_labexamplecom",
                "entry_field_key": "open_wifi",
            },
        ]

        responses = {
            "endpoint_corpexamplecom_av_gap": "high",
            "endpoint_corpexamplecom_open_wifi": "medium",
            "endpoint_labexamplecom_av_gap": "low",
            "endpoint_labexamplecom_open_wifi": "medium",
        }

        existing = {
            "endpoint": {
                "entries": [
                    {
                        "domain": "corp.example.com",
                        "av_gap": "medium",
                        "open_wifi": "low",
                        "_slug": "endpoint_corpexamplecom",
                    },
                    {
                        "domain": "lab.example.com",
                        "av_gap": "high",
                        "open_wifi": "high",
                        "_slug": "endpoint_labexamplecom",
                    },
                ],
                "domains_str": "corp.example.com/lab.example.com",
                "ood_count_str": "45/10",
                "wifi_count_str": "3/1",
                "ood_risk_string": "Medium/High",
                "wifi_risk_string": "Low/High",
            }
        }

        workbook_data = {
            "endpoint": {
                "domains": [
                    {"domain": "corp.example.com", "systems_ood": 45, "open_wifi": 3},
                    {"domain": "lab.example.com", "systems_ood": 10, "open_wifi": 1},
                ]
            }
        }

        grouped = _build_grouped_data_responses(
            responses,
            questions,
            existing_grouped=existing,
            workbook_data=workbook_data,
        )
        endpoint = grouped.get("endpoint", {})

        self.assertEqual(endpoint.get("domains_str"), "corp.example.com/lab.example.com")
        self.assertEqual(endpoint.get("ood_count_str"), "45/10")
        self.assertEqual(endpoint.get("wifi_count_str"), "3/1")
        self.assertEqual(endpoint.get("ood_risk_string"), "Medium/High")
        self.assertEqual(endpoint.get("wifi_risk_string"), "Low/High")

        entries = endpoint.get("entries", [])
        self.assertEqual(len(entries), 2)
        corp_entry = next(item for item in entries if item.get("domain") == "corp.example.com")
        lab_entry = next(item for item in entries if item.get("domain") == "lab.example.com")

        self.assertEqual(corp_entry.get("av_gap"), "high")
        self.assertEqual(corp_entry.get("open_wifi"), "medium")
        self.assertEqual(lab_entry.get("av_gap"), "low")
        self.assertEqual(lab_entry.get("open_wifi"), "medium")

    def test_endpoint_summary_generated_from_workbook_data(self):
        questions = [
            {
                "key": "endpoint_corpexamplecom_av_gap",
                "section_key": "endpoint",
                "subheading": "corp.example.com",
                "entry_slug": "endpoint_corpexamplecom",
                "entry_field_key": "av_gap",
            },
            {
                "key": "endpoint_corpexamplecom_open_wifi",
                "section_key": "endpoint",
                "subheading": "corp.example.com",
                "entry_slug": "endpoint_corpexamplecom",
                "entry_field_key": "open_wifi",
            },
        ]

        responses = {
            "endpoint_corpexamplecom_av_gap": "medium",
            "endpoint_corpexamplecom_open_wifi": "high",
        }

        workbook_data = {
            "endpoint": {
                "domains": [
                    {"domain": "corp.example.com", "systems_ood": 7, "open_wifi": 3},
                ]
            }
        }

        grouped = _build_grouped_data_responses(
            responses,
            questions,
            existing_grouped={},
            workbook_data=workbook_data,
        )

        endpoint = grouped.get("endpoint", {})
        self.assertEqual(endpoint.get("domains_str"), "corp.example.com")
        self.assertEqual(endpoint.get("ood_count_str"), "7")
        self.assertEqual(endpoint.get("wifi_count_str"), "3")
        self.assertEqual(endpoint.get("ood_risk_string"), "Medium")
        self.assertEqual(endpoint.get("wifi_risk_string"), "High")

        entries = endpoint.get("entries", [])
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.get("domain"), "corp.example.com")
        self.assertEqual(entry.get("av_gap"), "medium")
        self.assertEqual(entry.get("open_wifi"), "high")


class WorkbookEntryIsolationTests(SimpleTestCase):
    def test_nexpose_sections_do_not_share_state(self):
        class DummyProject:
            def __init__(self):
                self.workbook_data = {"external_nexpose": {"total": 4}}
                self.scoping = {}
                self.scoping_weights = {}

        project = DummyProject()

        payload = build_workbook_entry_payload(
            project=project,
            areas={
                "internal_nexpose": {
                    "total": 9,
                    "majority_type": "Insecure System Configurations",
                }
            },
        )

        self.assertEqual(payload["external_nexpose"].get("total"), 4)
        self.assertNotEqual(payload["external_nexpose"], payload["internal_nexpose"])
        self.assertEqual(payload["internal_nexpose"].get("total"), 9)
        self.assertEqual(
            payload["internal_nexpose"].get("majority_type"),
            "Insecure System Configurations",
        )
        self.assertIsNone(payload["external_nexpose"].get("majority_type"))
