# Standard Libraries
import logging
from datetime import datetime, timedelta

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.api.forms import ApiKeyForm

logging.disable(logging.CRITICAL)


class ApiKeyFormTests(TestCase):
    """Collection of tests for :form:`api.ApiKeyForm`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        expiry_date=None,
        **kwargs,
    ):
        return ApiKeyForm(
            data={
                "name": name,
                "expiry_date": expiry_date,
            },
        )

    def test_valid_data(self):
        form = self.form_data(name="Test Entry", expiry_date=datetime.now() + timedelta(days=1))
        self.assertTrue(form.is_valid())

    def test_empty_name(self):
        form = self.form_data(expiry_date=datetime.now())
        errors = form["name"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")

    def test_empty_date(self):
        form = self.form_data(name="No Date")
        errors = form["expiry_date"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")

    def test_expiry_date_in_past(self):
        form = self.form_data(name="Test Entry", expiry_date=datetime.now())
        errors = form["expiry_date"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_expiry_date")
