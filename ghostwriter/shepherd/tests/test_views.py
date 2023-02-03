# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter.factories import (
    AuxServerAddressFactory,
    ClientFactory,
    CloudServicesConfigurationFactory,
    DomainFactory,
    DomainNoteFactory,
    DomainServerConnectionFactory,
    DomainStatusFactory,
    HistoryFactory,
    NamecheapConfigurationFactory,
    ProjectFactory,
    ServerHistoryFactory,
    ServerNoteFactory,
    ServerStatusFactory,
    StaticServerFactory,
    TransientServerFactory,
    UserFactory,
    VirusTotalConfigurationFactory,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class IndexViewTests(TestCase):
    """Collection of tests for :view:`shepherd.index`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:index")
        cls.redirect_uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertRedirects(response, self.redirect_uri)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`shepherd.Domain`


class UpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.update`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:update")
        cls.vt_config = VirusTotalConfigurationFactory(enable=True)
        cls.cloud_config = CloudServicesConfigurationFactory(enable=True)
        cls.namecheap_config = NamecheapConfigurationFactory(enable=True)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/update.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("total_domains", response.context)
        self.assertIn("update_time", response.context)
        self.assertIn("enable_vt", response.context)
        self.assertIn("sleep_time", response.context)
        self.assertIn("cat_last_update_requested", response.context)
        self.assertIn("cat_last_update_completed", response.context)
        self.assertIn("cat_last_update_time", response.context)
        self.assertIn("cat_last_result", response.context)
        self.assertIn("dns_last_update_requested", response.context)
        self.assertIn("dns_last_update_completed", response.context)
        self.assertIn("dns_last_update_time", response.context)
        self.assertIn("dns_last_result", response.context)
        self.assertIn("enable_namecheap", response.context)
        self.assertIn("namecheap_last_update_requested", response.context)
        self.assertIn("namecheap_last_update_completed", response.context)
        self.assertIn("namecheap_last_update_time", response.context)
        self.assertIn("namecheap_last_result", response.context)
        self.assertIn("enable_cloud_monitor", response.context)
        self.assertIn("cloud_last_update_requested", response.context)
        self.assertIn("cloud_last_update_completed", response.context)
        self.assertIn("cloud_last_update_time", response.context)
        self.assertIn("cloud_last_result", response.context)

    def test_view_with_zero_sleep_time(self):
        self.vt_config.sleep_time = 0
        self.vt_config.save()
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_with_post_request(self):
        response = self.client_auth.post(self.uri)
        expected_url = reverse("shepherd:update")
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )


class DomainOverwatchViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ajax_domain_overwatch`."""

    @classmethod
    def setUpTestData(cls):
        cls.client_org = ClientFactory()
        cls.domain = DomainFactory()
        cls.unused_domain = DomainFactory()
        cls.checkout = HistoryFactory(client=cls.client_org, domain=cls.domain)
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:ajax_domain_overwatch")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_overwatch_warning_positive(self):
        post_data = {"client": self.client_org.pk, "domain": self.domain.pk}
        response = self.client_auth.get(self.uri, post_data)

        self.assertEqual(response.status_code, 200)
        data = {
            "result": "warning",
            "message": "Domain has been used with this client in the past",
        }
        self.assertJSONEqual(force_str(response.content), data)

    def test_overwatch_warning_negative(self):
        post_data = {"client": self.client_org.pk, "domain": self.unused_domain.pk}
        response = self.client_auth.get(self.uri, post_data)
        self.assertEqual(response.status_code, 200)
        data = {"result": "success", "message": ""}
        self.assertJSONEqual(force_str(response.content), data)

    def test_missing_values(self):
        post_data = {"domain": self.unused_domain.pk}
        response = self.client_auth.get(self.uri, post_data)
        self.assertEqual(response.status_code, 200)
        data = {"result": "error"}
        self.assertJSONEqual(force_str(response.content), data)


class DomainListViewTests(TestCase):
    """Collection of tests for :view:`shepherd.domain_list`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_domains = 10
        cls.domains = []
        for domain_id in range(cls.num_of_domains):
            name = f"domain{domain_id}.com"
            cls.domains.append(DomainFactory(name=name))

        cls.uri = reverse("shepherd:domains")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/domain_list.html")

    def test_lists_all_domains(self):
        # View defaults to showing only available domains, so nullify ``domain_status``
        response = self.client_auth.get(self.uri + "?domain_status=&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.domains))

    def test_search_domains(self):
        response = self.client_auth.get(self.uri + "?domain_search=domain2")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)

    def test_filter_domains(self):
        response = self.client_auth.get(self.uri + "?name=domain2&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)

    def test_blank_search(self):
        response = self.client_auth.get(self.uri + "?domain_search=")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.domains))


class DomainDetailViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.domain = DomainFactory()
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("shepherd:domain_detail", kwargs={"pk": cls.domain.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/domain_detail.html")


class DomainCreateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:domain_create")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/domain_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("shepherd:domains"))


class DomainUpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.domain = DomainFactory()
        cls.uri = reverse("shepherd:domain_update", kwargs={"pk": cls.domain.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/domain_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:domain_detail", kwargs={"pk": self.domain.pk}),
        )


class DomainDeleteViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.domain = DomainFactory()
        cls.Domain = DomainFactory._meta.model
        cls.uri = reverse("shepherd:domain_delete", kwargs={"pk": cls.domain.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:domain_detail", kwargs={"pk": self.domain.id}),
        )
        self.assertEqual(response.context["object_type"], "domain")
        self.assertEqual(response.context["object_to_be_deleted"], self.domain.name.upper())


class BurnViewTests(TestCase):
    """Collection of tests for :view:`shepherd.burn`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.domain = DomainFactory()
        cls.uri = reverse("shepherd:burn", kwargs={"pk": cls.domain.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/burn.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("domain_instance", response.context)
        self.assertIn("domain_name", response.context)
        self.assertIn("form", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:domain_detail", kwargs={"pk": self.domain.id}),
        )
        self.assertEqual(response.context["domain_instance"], self.domain)
        self.assertEqual(response.context["domain_name"], self.domain.name)


class DomainExportViewTests(TestCase):
    """Collection of tests for :view:`shepherd.export_domains_to_csv`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.num_of_domains = 10
        cls.domains = []
        for domain_id in range(cls.num_of_domains):
            cls.domains.append(DomainFactory())
        cls.uri = reverse("shepherd:export_domains_to_csv")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv")

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`shepherd.History`


class HistoryCreateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.HistoryCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.domain = DomainFactory()
        cls.uri = reverse("shepherd:history_create", kwargs={"pk": cls.domain.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/checkout.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("domain", response.context)
        self.assertIn("domain_name", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:domain_detail", kwargs={"pk": self.domain.id}),
        )
        self.assertEqual(response.context["domain"], self.domain)
        self.assertEqual(response.context["domain_name"], self.domain.name.upper())


class HistoryUpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.HistoryUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.entry = HistoryFactory()
        cls.uri = reverse("shepherd:history_update", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/checkout.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("domain_name", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#history".format(reverse("shepherd:domain_detail", kwargs={"pk": self.entry.domain.pk})),
        )
        self.assertEqual(response.context["domain_name"], self.entry.domain.name.upper())


class HistoryDeleteViewTests(TestCase):
    """Collection of tests for :view:`shepherd.HistoryDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.domain = DomainFactory()
        cls.entry = HistoryFactory(domain=cls.domain)
        cls.uri = reverse("shepherd:history_delete", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#history".format(reverse("shepherd:domain_detail", kwargs={"pk": self.domain.id})),
        )
        self.assertEqual(response.context["object_type"], "domain checkout")
        self.assertEqual(response.context["object_to_be_deleted"], self.entry)


class DomainReleaseViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainRelease`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.client_org = ClientFactory()

        cls.available_status = DomainStatusFactory(domain_status="Available")
        cls.unavailable_status = DomainStatusFactory(domain_status="Unavailable")
        cls.domain = DomainFactory(reset_dns=False, domain_status=cls.unavailable_status)

        cls.start_date = date.today() - timedelta(days=10)
        cls.end_date = date.today() + timedelta(days=20)
        cls.checkout = HistoryFactory(
            domain=cls.domain,
            operator=cls.user,
            start_date=cls.start_date,
            end_date=cls.end_date,
        )
        cls.other_user_checkout = HistoryFactory(domain=cls.domain, start_date=cls.start_date, end_date=cls.end_date)

        cls.uri = reverse("shepherd:ajax_domain_release", kwargs={"pk": cls.checkout.id})
        cls.failure_uri = reverse("shepherd:ajax_domain_release", kwargs={"pk": cls.other_user_checkout.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def tearDown(self):
        self.domain.domain_status = self.unavailable_status
        self.domain.save()
        self.checkout.end_date = self.end_date
        self.checkout.save()
        self.checkout.refresh_from_db()
        self.domain.refresh_from_db()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)

        self.domain.refresh_from_db()
        self.checkout.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        data = {"result": "success", "message": "Domain successfully released"}
        self.assertJSONEqual(force_str(response.content), data)
        self.assertEqual(self.domain.domain_status, self.available_status)
        self.assertEqual(self.checkout.end_date, date.today())

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_domain_release_failure(self):
        response = self.client_auth.post(self.failure_uri)
        self.assertEqual(response.status_code, 200)
        data = {
            "result": "error",
            "message": "You are not authorized to release this domain",
        }
        self.assertJSONEqual(force_str(response.content), data)
        self.assertFalse(self.domain.domain_status == self.available_status)
        self.assertTrue(self.checkout.end_date == self.end_date)


# Tests related to :model:`shepherd.StaticServer`


class ServerListViewTests(TestCase):
    """Collection of tests for :view:`shepherd.server_list`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_servers = 10
        cls.servers = []
        for server_id in range(cls.num_of_servers):
            name = f"server{server_id}.local"
            cls.servers.append(StaticServerFactory(name=name))

        cls.uri = reverse("shepherd:servers")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/server_list.html")

    def test_lists_all_servers(self):
        # View defaults to showing only available servers, so nullify ``server_status``
        response = self.client_auth.get(self.uri + "?server_status=&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.servers))

    def test_filter_servers(self):
        response = self.client_auth.get(self.uri + "?name=server2&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)


class ServerDetailViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.server = StaticServerFactory()
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("shepherd:server_detail", kwargs={"pk": cls.server.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/server_detail.html")


class ServerCreateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:server_create")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/server_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("addresses", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("shepherd:servers"))


class ServerUpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.server = StaticServerFactory()
        cls.uri = reverse("shepherd:server_update", kwargs={"pk": cls.server.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/server_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("addresses", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:server_detail", kwargs={"pk": self.server.pk}),
        )


class ServerDeleteViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.server = StaticServerFactory()
        cls.uri = reverse("shepherd:server_delete", kwargs={"pk": cls.server.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:server_detail", kwargs={"pk": self.server.id}),
        )
        self.assertEqual(response.context["object_type"], "static server")
        self.assertEqual(response.context["object_to_be_deleted"], self.server.ip_address)


class ServerExportViewTests(TestCase):
    """Collection of tests for :view:`shepherd.export_servers_to_csv`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.num_of_servers = 10
        cls.servers = []
        for server_id in range(cls.num_of_servers):
            cls.servers.append(StaticServerFactory())
        cls.uri = reverse("shepherd:export_servers_to_csv")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv")

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`shepherd.ServerHistory`


class ServerHistoryCreateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.HistoryCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.server = StaticServerFactory()
        cls.uri = reverse("shepherd:server_history_create", kwargs={"pk": cls.server.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/server_checkout.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("server_instance", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("shepherd:server_detail", kwargs={"pk": self.server.id}),
        )
        self.assertEqual(response.context["server_instance"], self.server)


class ServerHistoryUpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerHistoryUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.entry = ServerHistoryFactory()
        cls.uri = reverse("shepherd:server_history_update", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/server_checkout.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.entry.project.id})),
        )


class ServerHistoryDeleteViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerHistoryDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.entry = ServerHistoryFactory()
        cls.uri = reverse("shepherd:server_history_delete", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.entry.project.id})),
        )
        self.assertEqual(response.context["object_type"], "server checkout")
        self.assertEqual(response.context["object_to_be_deleted"], self.entry)


class ServerReleaseViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerRelease`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.client_org = ClientFactory()

        cls.available_status = ServerStatusFactory(server_status="Available")
        cls.unavailable_status = ServerStatusFactory(server_status="Unavailable")
        cls.server = StaticServerFactory(server_status=cls.unavailable_status)

        cls.start_date = date.today() - timedelta(days=10)
        cls.end_date = date.today() + timedelta(days=20)
        cls.checkout = ServerHistoryFactory(
            server=cls.server,
            operator=cls.user,
            start_date=cls.start_date,
            end_date=cls.end_date,
        )
        cls.other_user_checkout = ServerHistoryFactory(
            server=cls.server, start_date=cls.start_date, end_date=cls.end_date
        )

        cls.uri = reverse("shepherd:ajax_server_release", kwargs={"pk": cls.checkout.id})
        cls.failure_uri = reverse("shepherd:ajax_server_release", kwargs={"pk": cls.other_user_checkout.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def tearDown(self):
        self.server.server_status = self.unavailable_status
        self.server.save()
        self.checkout.end_date = self.end_date
        self.checkout.save()
        self.checkout.refresh_from_db()
        self.server.refresh_from_db()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)

        self.server.refresh_from_db()
        self.checkout.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        data = {"result": "success", "message": "Server successfully released"}
        self.assertJSONEqual(force_str(response.content), data)
        self.assertEqual(self.server.server_status, self.available_status)
        self.assertEqual(self.checkout.end_date, date.today())

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_domain_release_failure(self):
        response = self.client_auth.post(self.failure_uri)
        self.assertEqual(response.status_code, 200)
        data = {
            "result": "error",
            "message": "You are not authorized to release this server",
        }
        self.assertJSONEqual(force_str(response.content), data)
        self.assertFalse(self.server.server_status == self.available_status)
        self.assertTrue(self.checkout.end_date == self.end_date)


# Tests related to :model:`shepherd.TransientServer`


class TransientServerCreateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.TransientServerCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.project = ProjectFactory()
        cls.uri = reverse("shepherd:vps_create", kwargs={"pk": cls.project.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/vps_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.project.id})),
        )


class TransientServerUpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.TransientServerUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.server = TransientServerFactory()
        cls.uri = reverse("shepherd:vps_update", kwargs={"pk": cls.server.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/vps_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.server.project.id})),
        )


class TransientServerDeleteViewTests(TestCase):
    """Collection of tests for :view:`shepherd.TransientServerDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.server = TransientServerFactory()
        cls.TransientServer = TransientServerFactory._meta.model
        cls.uri = reverse("shepherd:ajax_delete_vps", kwargs={"pk": cls.server.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.TransientServer.objects.all().exists())
        data = {"result": "success", "message": "VPS successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`shepherd.DomainServerConnection`


class DomainServerConnectionCreateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainServerConnectionCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.project = ProjectFactory()
        cls.uri = reverse("shepherd:link_create", kwargs={"pk": cls.project.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/connect_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.project.id})),
        )


class DomainServerConnectionUpdateViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainServerConnectionUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.entry = DomainServerConnectionFactory()
        cls.uri = reverse("shepherd:link_update", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/connect_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.entry.project.id})),
        )


class DomainServerConnectionDeleteViewTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainServerConnectionDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.entry = DomainServerConnectionFactory()
        cls.DomainServerConnection = DomainServerConnectionFactory._meta.model
        cls.uri = reverse("shepherd:ajax_delete_domain_link", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.DomainServerConnection.objects.all().exists())
        data = {"result": "success", "message": "Link successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to multi-model views


class UserAssetsViewTests(TestCase):
    """Collection of tests for :view:`shepherd.user_assets`."""

    @classmethod
    def setUpTestData(cls):
        cls.History = HistoryFactory._meta.model
        cls.ServerHistory = ServerHistoryFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

        domain_status = DomainStatusFactory(domain_status="Unavailable")
        server_status = ServerStatusFactory(server_status="Unavailable")

        for x in range(3):
            HistoryFactory(operator=cls.user, domain=DomainFactory(domain_status=domain_status))
            ServerHistoryFactory(
                operator=cls.user,
                server=StaticServerFactory(server_status=server_status),
            )

        cls.domains_qs = cls.History.objects.all().order_by("end_date")
        cls.servers_qs = cls.ServerHistory.objects.all().order_by("end_date")

        cls.uri = reverse("shepherd:user_assets")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shepherd/checkouts_for_user.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("domains", response.context)
        self.assertIn("servers", response.context)

        self.assertEqual(len(response.context["domains"]), len(self.domains_qs))
        self.assertEqual(len(response.context["servers"]), len(self.servers_qs))


class ServerSearchViewTests(TestCase):
    """Collection of tests for :view:`shepherd.server_search`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.server_status = ServerStatusFactory(server_status="Unavailable")
        cls.project = ProjectFactory()

        cls.servers = []
        cls.addresses = []
        for x in range(3):
            server = StaticServerFactory(ip_address=f"192.168.1.{x}")
            addy = AuxServerAddressFactory(ip_address=f"192.168.2.{x}", static_server=server)
            cls.servers.append(server)
            cls.addresses.append(addy)

        cls.unavailable_server = StaticServerFactory(ip_address="192.168.3.30", server_status=cls.server_status)
        cls.unavailable_aux_address = AuxServerAddressFactory(
            ip_address="192.168.3.31", static_server=cls.unavailable_server
        )

        cls.uri = reverse("shepherd:server_search")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        post_data = {
            "server_search": self.servers[0].ip_address,
            "project_id": self.project.id,
        }
        response = self.client_auth.post(self.uri, post_data)
        expected_url = reverse("shepherd:server_checkout", kwargs={"pk": self.servers[0].id})
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )

    def test_unavailable_server_match(self):
        post_data = {
            "server_search": self.unavailable_server.ip_address,
            "project_id": self.project.id,
        }
        response = self.client_auth.post(self.uri, post_data)
        expected_url = "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.project.id}))
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )

    def test_aux_address_match(self):
        post_data = {
            "server_search": self.addresses[0].ip_address,
            "project_id": self.project.id,
        }
        response = self.client_auth.post(self.uri, post_data)
        expected_url = reverse("shepherd:server_checkout", kwargs={"pk": self.addresses[0].static_server.id})
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )

    def test_unavailable_aux_address_match(self):
        post_data = {
            "server_search": self.unavailable_aux_address.ip_address,
            "project_id": self.project.id,
        }
        response = self.client_auth.post(self.uri, post_data)
        expected_url = "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.project.id}))
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )

    def test_view_requires_login(self):
        post_data = {"server_search": "192.168.1.1", "project_id": self.project.id}
        response = self.client.post(self.uri, post_data)
        self.assertEqual(response.status_code, 302)


class InfrastructureSearchViewTests(TestCase):
    """Collection of tests for :view:`shepherd.infrastructure_search`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.servers = []
        cls.addresses = []
        cls.cloud_servers = []
        for x in range(3):
            server = StaticServerFactory(ip_address=f"192.168.1.{x}")
            addy = AuxServerAddressFactory(ip_address=f"192.168.2.{x}", static_server=server)
            vps = TransientServerFactory(ip_address=f"192.168.3.{x}")
            cls.servers.append(server)
            cls.addresses.append(addy)
            cls.cloud_servers.append(vps)

        cls.total = len(cls.servers) + len(cls.addresses) + len(cls.cloud_servers)

        cls.uri = reverse("shepherd:infrastructure_search")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        post_data = {"query": "192.168.1.1"}
        response = self.client_auth.get(self.uri, post_data)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        post_data = {"query": "192.168.1.1"}
        response = self.client.get(self.uri, post_data)
        self.assertEqual(response.status_code, 302)

    def test_custom_context_exists(self):
        post_data = {"query": "192.168"}
        response = self.client_auth.get(self.uri, post_data)
        self.assertEqual(response.status_code, 200)

        self.assertIn("servers", response.context)
        self.assertIn("vps", response.context)
        self.assertIn("addresses", response.context)
        self.assertIn("total_result", response.context)

        self.assertEqual(len(response.context["servers"]), len(self.servers))
        self.assertEqual(len(response.context["vps"]), len(self.cloud_servers))
        self.assertEqual(len(response.context["addresses"]), len(self.addresses))
        self.assertEqual(response.context["total_result"], self.total)

    def test_custom_context_with_few_results(self):
        post_data = {"query": "192.168.2"}
        response = self.client_auth.get(self.uri, post_data)
        self.assertEqual(response.status_code, 200)

        self.assertIn("servers", response.context)
        self.assertIn("vps", response.context)
        self.assertIn("addresses", response.context)
        self.assertIn("total_result", response.context)

        self.assertEqual(len(response.context["servers"]), 0)
        self.assertEqual(len(response.context["vps"]), 0)
        self.assertEqual(len(response.context["addresses"]), len(self.addresses))
        self.assertEqual(response.context["total_result"], 3)

    def test_blank_search(self):
        response = self.client_auth.get(self.uri + "?query=")
        self.assertEqual(response.status_code, 200)

    def test_search_with_zero_results(self):
        post_data = {"query": "1.1.1.1"}
        response = self.client_auth.get(self.uri, post_data)
        self.assertEqual(response.status_code, 200)

        self.assertIn("servers", response.context)
        self.assertIn("vps", response.context)
        self.assertIn("addresses", response.context)
        self.assertIn("total_result", response.context)

        self.assertEqual(len(response.context["servers"]), 0)
        self.assertEqual(len(response.context["vps"]), 0)
        self.assertEqual(len(response.context["addresses"]), 0)
        self.assertEqual(response.context["total_result"], 0)


class UpdateDomainBadgesViewTests(TestCase):
    """Collection of tests for :view:`shepherd.update_domain_badges`."""

    @classmethod
    def setUpTestData(cls):
        cls.domain = DomainFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:ajax_update_domain_badges", kwargs={"pk": cls.domain.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class LoadProjectsViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ajax_load_projects`."""

    @classmethod
    def setUpTestData(cls):
        cls.org = ClientFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:ajax_load_projects") + "?client=%s" % cls.org.id

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class LoadProjectViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ajax_load_project`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("shepherd:ajax_load_project") + "?project=%s" % cls.project.id

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_project_data_access(self):
        response = self.client_auth.get(self.uri)
        json_data = response.json()[0]
        self.assertEqual(json_data["fields"]["codename"], self.project.codename)


class ProjectDomainsViewTests(TestCase):
    """Collection of tests for :view:`shepherd.ajax_project_domains`."""

    @classmethod
    def setUpTestData(cls):
        cls.History = HistoryFactory._meta.model
        cls.project = ProjectFactory()
        cls.no_checkout_project = ProjectFactory()
        HistoryFactory.create_batch(3, project=cls.project)

        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("shepherd:ajax_project_domains", kwargs={"pk": cls.project.id})
        cls.no_checkout_uri = reverse("shepherd:ajax_project_domains", kwargs={"pk": cls.no_checkout_project.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_with_no_history(self):
        response = self.client_auth.get(self.no_checkout_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_with_no_checkout_records(self):
        response = self.client_auth.get(self.no_checkout_uri)
        self.assertEqual(response.status_code, 200)


class DomainNoteUpdateTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.DomainNote = DomainNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = DomainNoteFactory(operator=cls.user)
        cls.uri = reverse("shepherd:domain_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = DomainNoteFactory()
        cls.other_user_uri = reverse("shepherd:domain_note_edit", kwargs={"pk": cls.other_user_note.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class DomainNoteDeleteTests(TestCase):
    """Collection of tests for :view:`shepherd.DomainNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.DomainNote = DomainNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        self.DomainNote.objects.all().delete()
        note = DomainNoteFactory(operator=self.user)
        uri = reverse("shepherd:ajax_delete_domain_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.DomainNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.DomainNote.objects.all()), 0)

    def test_view_permissions(self):
        note = DomainNoteFactory()
        uri = reverse("shepherd:ajax_delete_domain_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = DomainNoteFactory()
        uri = reverse("shepherd:ajax_delete_domain_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)


class ServerNoteUpdateTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerNote = ServerNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = ServerNoteFactory(operator=cls.user)
        cls.uri = reverse("shepherd:server_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = ServerNoteFactory()
        cls.other_user_uri = reverse("shepherd:server_note_edit", kwargs={"pk": cls.other_user_note.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ServerNoteDeleteTests(TestCase):
    """Collection of tests for :view:`shepherd.ServerNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerNote = ServerNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        self.ServerNote.objects.all().delete()
        note = ServerNoteFactory(operator=self.user)
        uri = reverse("shepherd:ajax_delete_server_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.ServerNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.ServerNote.objects.all()), 0)

    def test_view_permissions(self):
        note = ServerNoteFactory()
        uri = reverse("shepherd:ajax_delete_server_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = ServerNoteFactory()
        uri = reverse("shepherd:ajax_delete_server_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)
