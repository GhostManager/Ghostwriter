# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.rolodex.risk import build_project_risk_summary


class BuildProjectRiskSummaryTests(TestCase):
    """Tests for risk-summary extraction from workbook payloads."""

    def test_accepts_direct_report_card_risk_label(self):
        workbook_payload = {"report_card": {"overall": "Medium"}}

        summary = build_project_risk_summary(workbook_payload)

        self.assertEqual(summary.get("overall_risk"), "Medium")

    def test_accepts_transition_report_card_risk_label(self):
        workbook_payload = {"report_card": {"overall": "Medium-->High"}}

        summary = build_project_risk_summary(workbook_payload)

        self.assertEqual(summary.get("overall_risk"), "Medium-->High")

    def test_still_maps_letter_grade_values(self):
        workbook_payload = {"report_card": {"overall": "B"}}

        summary = build_project_risk_summary(workbook_payload)

        self.assertEqual(summary.get("overall_risk"), "Medium")

    def test_omits_unknown_report_card_values(self):
        workbook_payload = {"report_card": {"overall": "NotARiskLabel"}}

        summary = build_project_risk_summary(workbook_payload)

        self.assertNotIn("overall_risk", summary)
