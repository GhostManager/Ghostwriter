# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ClientFactory,
    DomainFactory,
    DomainNoteFactory,
    DomainServerConnectionFactory,
    DomainStatusFactory,
    HistoryFactory,
    ProjectFactory,
    ServerHistoryFactory,
    ServerNoteFactory,
    TransientServerFactory,
)
from ghostwriter.shepherd.forms import (
    BurnForm,
    CheckoutForm,
    DomainForm,
    DomainLinkForm,
    DomainNoteForm,
)
from ghostwriter.shepherd.forms_server import ServerNoteForm

logging.disable(logging.INFO)


class CheckoutFormTests(TestCase):
    """Collection of tests for :form:`shepherd.CheckoutForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.unavailable_status = DomainStatusFactory(domain_status="Unavailable")
        cls.domain = DomainFactory(expiration=date.today() + timedelta(days=360))
        cls.unavailable_domain = DomainFactory(
            domain_status=cls.unavailable_status,
            expiration=date.today() + timedelta(days=360),
        )
        cls.expired_domain = DomainFactory(expiration=date.today() - timedelta(days=30))
        cls.project = ProjectFactory()

    def setUp(self):
        pass

    def form_data(
        self,
        start_date=None,
        end_date=None,
        note=None,
        domain_id=None,
        client_id=None,
        project_id=None,
        activity_type_id=None,
        **kwargs,
    ):
        return CheckoutForm(
            data={
                "start_date": start_date,
                "end_date": end_date,
                "note": note,
                "domain": domain_id,
                "client": client_id,
                "project": project_id,
                "activity_type": activity_type_id,
            },
        )

    def test_valid_data(self):
        checkout = HistoryFactory(
            client=self.project.client, project=self.project, domain=self.domain
        )
        form = self.form_data(**checkout.__dict__)
        self.assertTrue(form.is_valid())

    def test_invalid_dates(self):
        end_date = date.today()
        start_date = date.today() + timedelta(days=20)
        checkout = HistoryFactory(
            client=self.project.client,
            project=self.project,
            domain=self.domain,
            start_date=start_date,
            end_date=end_date,
        )
        form = self.form_data(**checkout.__dict__)
        errors = form["end_date"].errors.as_data()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")

    def test_unavailable_domain(self):
        checkout = HistoryFactory(
            client=self.project.client,
            project=self.project,
            domain=self.unavailable_domain,
        )
        form = self.form_data(**checkout.__dict__)
        errors = form["domain"].errors.as_data()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "unavailable")

    def test_expired_domain(self):
        checkout = HistoryFactory(
            client=self.project.client, project=self.project, domain=self.expired_domain
        )
        form = self.form_data(**checkout.__dict__)
        errors = form["domain"].errors.as_data()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "expired")


class DomainFormTests(TestCase):
    """Collection of tests for :form:`shepherd.DomainForm`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        registrar=None,
        creation=None,
        expiration=None,
        last_health_check=None,
        vt_permalink=None,
        ibm_xforce_cat=None,
        talos_cat=None,
        bluecoat_cat=None,
        fortiguard_cat=None,
        opendns_cat=None,
        trendmicro_cat=None,
        mx_toolbox_status=None,
        note=None,
        burned_explanation=None,
        auto_renew=None,
        reset_dns=None,
        whois_status_id=None,
        health_status_id=None,
        domain_status_id=None,
        **kwargs,
    ):
        return DomainForm(
            data={
                "name": name,
                "registrar": registrar,
                "creation": creation,
                "expiration": expiration,
                "last_health_check": last_health_check,
                "vt_permalink": vt_permalink,
                "ibm_xforce_cat": ibm_xforce_cat,
                "talos_cat": talos_cat,
                "bluecoat_cat": bluecoat_cat,
                "fortiguard_cat": fortiguard_cat,
                "opendns_cat": opendns_cat,
                "trendmicro_cat": trendmicro_cat,
                "mx_toolbox_status": mx_toolbox_status,
                "note": note,
                "burned_explanation": burned_explanation,
                "auto_renew": auto_renew,
                "reset_dns": reset_dns,
                "whois_status": whois_status_id,
                "health_status": health_status_id,
                "domain_status": domain_status_id,
            },
        )

    def test_valid_data(self):
        start_date = date.today()
        end_date = date.today() + timedelta(days=360)
        domain = DomainFactory()
        domain_dict = domain.__dict__
        domain_dict["name"] = "soemthing.new"
        domain_dict["creation"] = start_date
        domain_dict["expiration"] = end_date

        form = self.form_data(**domain_dict)
        self.assertTrue(form.is_valid())

    def test_invalid_dates(self):
        end_date = date.today()
        start_date = date.today() + timedelta(days=360)
        domain = DomainFactory()
        domain_dict = domain.__dict__
        domain_dict["name"] = "soemthing.new"
        domain_dict["creation"] = start_date
        domain_dict["expiration"] = end_date

        form = self.form_data(**domain.__dict__)
        errors = form.errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors["__all__"][0].code, "invalid_date")


class DomainLinkFormTests(TestCase):
    """Collection of tests for :form:`shepherd.DomainLinkForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.domain = HistoryFactory(project=cls.project)
        cls.server = ServerHistoryFactory(project=cls.project)
        cls.vps = TransientServerFactory(project=cls.project)
        cls.link = DomainServerConnectionFactory(
            project=cls.project,
            domain=cls.domain,
            static_server=cls.server,
            transient_server=None,
        )
        cls.link_dict = cls.link.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        domain_id=None,
        static_server_id=None,
        transient_server_id=None,
        activity_type_id=None,
        project_id=None,
        **kwargs,
    ):
        return DomainLinkForm(
            data={
                "domain": domain_id,
                "static_server": static_server_id,
                "transient_server": transient_server_id,
                "activity_type": activity_type_id,
                "project": project_id,
            },
            project=self.project,
        )

    def test_valid_data(self):
        link = self.link_dict.copy()
        form = self.form_data(**link)
        self.assertTrue(form.is_valid())

    def test_selecting_two_servers(self):
        link = self.link_dict.copy()
        link["transient_server_id"] = self.vps
        form = self.form_data(**link)
        errors = form.errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors["__all__"][0].code, "invalid_selection")


class BurnFormTests(TestCase):
    """Collection of tests for :form:`shepherd.BurnForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.domain = DomainFactory()
        cls.domain_dict = cls.domain.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        burned_explanation=None,
        **kwargs,
    ):
        return BurnForm(
            data={
                "burned_explanation": burned_explanation,
            },
        )

    def test_valid_data(self):
        domain = self.domain_dict.copy()
        form = self.form_data(**domain)
        self.assertTrue(form.is_valid())


class DomainNoteFormTests(TestCase):
    """Collection of tests for :form:`shepherd.DomainNoteForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.note = DomainNoteFactory()
        cls.note_dict = cls.note.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        note=None,
        **kwargs,
    ):
        return DomainNoteForm(
            data={
                "note": note,
            },
        )

    def test_valid_data(self):
        note = self.note_dict.copy()

        form = self.form_data(**note)
        self.assertTrue(form.is_valid())

    def test_blank_note(self):
        note = self.note_dict.copy()
        note["note"] = ""

        form = self.form_data(**note)
        errors = form["note"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")


class ServerNoteFormTests(TestCase):
    """Collection of tests for :form:`shepherd.ServerNoteForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.note = ServerNoteFactory()
        cls.note_dict = cls.note.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        note=None,
        **kwargs,
    ):
        return ServerNoteForm(
            data={
                "note": note,
            },
        )

    def test_valid_data(self):
        note = self.note_dict.copy()

        form = self.form_data(**note)
        self.assertTrue(form.is_valid())

    def test_blank_note(self):
        note = self.note_dict.copy()
        note["note"] = ""

        form = self.form_data(**note)
        errors = form["note"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")
