# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    AuxServerAddressFactory,
    DomainFactory,
    DomainNoteFactory,
    DomainServerConnectionFactory,
    DomainStatusFactory,
    HistoryFactory,
    ProjectFactory,
    ServerHistoryFactory,
    ServerNoteFactory,
    ServerStatusFactory,
    StaticServerFactory,
    TransientServerFactory,
)
from ghostwriter.shepherd.forms import (
    BurnForm,
    CheckoutForm,
    DomainForm,
    DomainLinkForm,
    DomainNoteForm,
)
from ghostwriter.shepherd.forms_server import (
    AuxServerAddressForm,
    ServerAddressFormSet,
    ServerCheckoutForm,
    ServerForm,
    ServerNoteForm,
    TransientServerForm,
)

logging.disable(logging.CRITICAL)


def instantiate_formset(formset_class, data, instance=None, initial=None):
    prefix = formset_class().prefix
    formset_data = {}
    for i, form_data in enumerate(data):
        for name, value in form_data.items():
            if isinstance(value, list):
                for j, inner in enumerate(value):
                    formset_data["{}-{}-{}_{}".format(prefix, i, name, j)] = inner
            else:
                formset_data["{}-{}-{}".format(prefix, i, name)] = value
    formset_data["{}-TOTAL_FORMS".format(prefix)] = len(data)
    formset_data["{}-INITIAL_FORMS".format(prefix)] = 0

    if instance:
        return formset_class(formset_data, instance=instance, initial=initial)
    else:
        return formset_class(formset_data, initial=initial)


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
        checkout = HistoryFactory(client=self.project.client, project=self.project, domain=self.domain)
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
        checkout = HistoryFactory(client=self.project.client, project=self.project, domain=self.expired_domain)
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
        domain_dict["name"] = "something.new"
        domain_dict["creation"] = start_date
        domain_dict["expiration"] = end_date

        form = self.form_data(**domain_dict)
        self.assertTrue(form.is_valid())

    def test_invalid_dates(self):
        end_date = date.today()
        start_date = date.today() + timedelta(days=360)
        domain = DomainFactory()
        domain_dict = domain.__dict__
        domain_dict["name"] = "something.new"
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

    def test_selecting_zero_servers(self):
        link = self.link_dict.copy()
        link["static_server_id"] = None
        link["transient_server_id"] = None
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


# TODO


class AuxServerAddressFormTests(TestCase):
    """Collection of tests for :form:`shepherd.AuxServerAddressForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.address = AuxServerAddressFactory()
        cls.address_dict = cls.address.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        primary=None,
        ip_address=None,
        static_server=None,
        **kwargs,
    ):
        return AuxServerAddressForm(
            data={
                "primary": primary,
                "ip_address": ip_address,
                "static_server": static_server,
            },
        )

    def test_valid_data(self):
        address = self.address_dict.copy()

        form = self.form_data(**address)
        self.assertTrue(form.is_valid())


class ServerAddressFormSetTests(TestCase):
    """Collection of tests for :form:`shepherd.ServerAddressFormSet`."""

    @classmethod
    def setUpTestData(cls):
        cls.server = StaticServerFactory()
        cls.server_dict = cls.server.__dict__
        cls.aux_addy_1 = AuxServerAddressFactory(static_server=cls.server, primary=False)
        cls.aux_addy_2 = AuxServerAddressFactory(static_server=cls.server, primary=False)
        cls.to_be_deleted = AuxServerAddressFactory(static_server=cls.server, primary=False)

    def form_data(self, data, **kwargs):
        return instantiate_formset(ServerAddressFormSet, data=data, instance=self.server)

    def test_valid_data(self):
        data = [self.aux_addy_1.__dict__, self.aux_addy_2.__dict__]
        form = self.form_data(data)
        self.assertTrue(form.is_valid())

    def test_multiple_primary_addresses(self):
        addy_1 = self.aux_addy_1.__dict__.copy()
        addy_2 = self.aux_addy_2.__dict__.copy()
        addy_1["primary"] = True
        addy_2["primary"] = True

        data = [addy_1, addy_2]
        form = self.form_data(data)
        errors = form.errors[1]["primary"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_duplicate_address(self):
        addy_1 = self.aux_addy_1.__dict__.copy()
        addy_2 = self.aux_addy_2.__dict__.copy()
        addy_2["ip_address"] = addy_1["ip_address"]

        data = [addy_1, addy_2]
        form = self.form_data(data)
        errors = form.errors[1]["ip_address"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_incomplete_address_form(self):
        addy_1 = self.aux_addy_1.__dict__.copy()
        addy_2 = self.aux_addy_2.__dict__.copy()
        addy_1["ip_address"] = ""
        addy_1["primary"] = True

        data = [addy_1, addy_2]
        form = self.form_data(data)
        errors = form.errors[0]["ip_address"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_address_delete(self):
        addy_1 = self.aux_addy_1.__dict__.copy()
        addy_2 = self.aux_addy_2.__dict__.copy()
        addy_1["ip_address"] = ""
        addy_1["primary"] = True
        addy_1["DELETE"] = True

        data = [addy_1, addy_2]
        form = self.form_data(data)
        self.assertTrue(form.is_valid())


class ServerFormTests(TestCase):
    """Collection of tests for :form:`shepherd.ServerForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.server = StaticServerFactory()
        cls.server_dict = cls.server.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        ip_address=None,
        name=None,
        server_status_id=None,
        server_provider_id=None,
        note=None,
        **kwargs,
    ):
        return ServerForm(
            data={
                "ip_address": ip_address,
                "name": name,
                "server_status": server_status_id,
                "server_provider": server_provider_id,
                "note": note,
            },
        )

    def test_valid_data(self):
        server = self.server_dict.copy()
        server["ip_address"] = "1.1.1.1"

        form = self.form_data(**server)
        self.assertTrue(form.is_valid())


class ServerCheckoutFormSetTests(TestCase):
    """Collection of tests for :form:`shepherd.ServerCheckoutForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.unavailable_status = ServerStatusFactory(server_status="Unavailable")
        cls.server = StaticServerFactory()
        cls.unavailable_server = StaticServerFactory(server_status=cls.unavailable_status)
        cls.project = ProjectFactory()

    def setUp(self):
        pass

    def form_data(
        self,
        server_id=None,
        start_date=None,
        end_date=None,
        note=None,
        client_id=None,
        project_id=None,
        activity_type_id=None,
        server_role_id=None,
        **kwargs,
    ):
        return ServerCheckoutForm(
            data={
                "start_date": start_date,
                "end_date": end_date,
                "note": note,
                "server": server_id,
                "server_role": server_role_id,
                "client": client_id,
                "project": project_id,
                "activity_type": activity_type_id,
            },
        )

    def test_valid_data(self):
        checkout = ServerHistoryFactory(client=self.project.client, project=self.project, server=self.server)

        form = self.form_data(**checkout.__dict__)
        self.assertTrue(form.is_valid())

    def test_invalid_dates(self):
        end_date = date.today()
        start_date = date.today() + timedelta(days=20)
        checkout = ServerHistoryFactory(
            client=self.project.client,
            project=self.project,
            server=self.server,
            start_date=start_date,
            end_date=end_date,
        )
        form = self.form_data(**checkout.__dict__)
        errors = form["end_date"].errors.as_data()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")

    def test_unavailable_server(self):
        checkout = ServerHistoryFactory(
            client=self.project.client,
            project=self.project,
            server=self.unavailable_server,
        )
        form = self.form_data(**checkout.__dict__)
        errors = form["server"].errors.as_data()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "unavailable")


class TransientServerFormTests(TestCase):
    """Collection of tests for :form:`shepherd.TransientServerForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.server = TransientServerFactory(project=cls.project)
        cls.server_dict = cls.server.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        ip_address=None,
        aux_address=None,
        name=None,
        activity_type_id=None,
        server_role_id=None,
        server_provider_id=None,
        note=None,
        project_id=None,
        **kwargs,
    ):
        return TransientServerForm(
            data={
                "ip_address": ip_address,
                "aux_address": aux_address,
                "aux_address_0": aux_address[0],
                "aux_address_1": aux_address[1],
                "aux_address_2": aux_address[2],
                "name": name,
                "activity_type": activity_type_id,
                "server_role": server_role_id,
                "server_provider": server_provider_id,
                "note": note,
                "project": project_id,
            },
        )

    def test_valid_data(self):
        server = self.server_dict.copy()
        server["ip_address"] = "1.1.1.1"

        form = self.form_data(**server)
        self.assertTrue(form.is_valid())
