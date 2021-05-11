import factory
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from model_bakery import baker

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """
    Create a new :model:`users.User` with no privileges.
    """

    class Meta:
        model = User

    name = "Benny Ghostwriter"
    email = "benny@getghostwriter.io)"
    password = factory.PostGenerationMethodCall(
        "set_password", "SupernaturalReporting_1337!"
    )
    is_superuser = False
    is_staff = False
    is_active = True


class TestReportList(TestCase):
    """
    Test :form:`views.reports_list`.
    """

    def setUp(self):
        # Setup models
        self.num_of_reports = 10
        self.reports = []
        first_report = True
        for report_id in range(self.num_of_reports):
            title = "Report{}".format(report_id)
            if first_report:
                complete = True
                first_report = False
            else:
                complete = False
            self.reports.append(
                baker.make(
                    "reporting.Report",
                    title=title,
                    complete=complete,
                )
            )

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:reports")

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_list.html")

    def test_lists_all_reports(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == self.num_of_reports)

    def test_filter_reports(self):
        response = self.client.get(self.url + "?title=&complete=1&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)


class TestReportDetailView(TestCase):
    """
    Test :form:`views.ReportDetailView`.
    """

    def setUp(self):
        # Setup models
        self.report_client = baker.make("rolodex.Client", name="Test")
        self.project_type = baker.make("rolodex.ProjectType", project_type="Red Team")
        self.report_project = baker.make(
            "rolodex.Project", client=self.report_client, project_type=self.project_type
        )
        self.report = baker.make("reporting.Report", project=self.report_project)
        self.num_of_findings = 10
        self.findings = []
        for finding_id in range(self.num_of_findings):
            title = "Finding{}".format(finding_id)
            self.findings.append(
                baker.make(
                    "reporting.ReportFindingLink",
                    title=title,
                    report=self.report,
                )
            )

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:report_detail", kwargs={"pk": self.report.pk})

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_detail.html")


class TestReportUpdate(TestCase):
    """
    Test :form:`views.ReportUpdate`.
    """

    def setUp(self):
        # Setup models
        self.report = baker.make("reporting.Report")

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:report_update", kwargs={"pk": self.report.pk})

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_form.html")

    def test_cancel_link_exists(self):
        response = self.client.get(self.url)
        self.assertIn("cancel_link", response.context)


class TestReportDelete(TestCase):
    """
    Test :form:`views.ReportDelete`.
    """

    def setUp(self):
        # Setup models
        self.report = baker.make("reporting.Report")

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:report_delete", kwargs={"pk": self.report.pk})

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client.get(self.url)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)


class TestFindingList(TestCase):
    """
    Test :form:`views.findings_list`.
    """

    def setUp(self):
        # Setup models
        self.num_of_findings = 10
        self.findings = []
        for finding_id in range(self.num_of_findings):
            title = "Finding{}".format(finding_id)
            self.findings.append(
                baker.make("reporting.Finding", title=title, _fill_optional=True)
            )

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:findings")

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_list.html")

    def test_lists_all_findings(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == self.num_of_findings)

    def test_search_findings(self):
        response = self.client.get(self.url + "?finding_search=Finding1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)

    def test_filter_findings(self):
        response = self.client.get(self.url + "?title=Finding1&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)


class TestFindingDetailView(TestCase):
    """
    Test :form:`views.FindingDetailView`.
    """

    def setUp(self):
        # Setup models
        self.finding = baker.make(
            "reporting.Finding", title="Finding #1", _fill_optional=True
        )
        self.finding_note = baker.make("reporting.FindingNote", finding=self.finding)

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:finding_detail", kwargs={"pk": self.finding.pk})

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_detail.html")


class TestFindingUpdate(TestCase):
    """
    Test :form:`views.FindingUpdate`.
    """

    def setUp(self):
        # Setup models
        self.finding = baker.make(
            "reporting.Finding", title="Finding #1", _fill_optional=True
        )

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:finding_update", kwargs={"pk": self.finding.pk})

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_form.html")

    def test_cancel_link_exists(self):
        response = self.client.get(self.url)
        self.assertIn("cancel_link", response.context)


class TestFindingDelete(TestCase):
    """
    Test :form:`views.FindingDelete`.
    """

    def setUp(self):
        # Setup models
        self.finding = baker.make(
            "reporting.Finding", title="Finding #1", _fill_optional=True
        )

        # Setup users
        self.user = UserFactory()
        self.client.login(username=self.user, password="SupernaturalReporting_1337!")

        # View to test
        self.url = reverse("reporting:finding_delete", kwargs={"pk": self.finding.pk})

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client.get(self.url)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
