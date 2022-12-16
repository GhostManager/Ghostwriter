"""This contains all the forms used by the API application."""

# Standard Libraries
from datetime import timedelta

# Django Imports
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Field, Layout, Row, Submit


class ApiKeyForm(forms.Form):
    """
    Save an individual :model:`oplog.Oplog`.
    """

    name = forms.CharField()
    expiry_date = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M"],
    )

    class Meta:
        fields = [
            "name",
            "expiry_date",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["expiry_date"].label = "Expiry Date & Time"
        self.fields["expiry_date"].widget.input_type = "datetime-local"
        self.fields["expiry_date"].initial = timezone.now() + timedelta(days=1)
        self.fields[
            "expiry_date"
        ].help_text = f"Pick a date / time and then select AM or PM (uses server's time zone–{settings.TIME_ZONE})"
        self.fields["name"].help_text = "Enter a name to help you identify this API key later"
        self.fields["name"].widget.attrs["placeholder"] = "API Token – Automation Script"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-6 mb-0"),
                Column(Field("expiry_date", step=1), css_class="form-group col-6 mb-0"),
                css_class="form-group",
            ),
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data["expiry_date"]

        # Check if expiration comes before the creation date
        if expiry_date:
            if expiry_date < timezone.now():
                raise ValidationError(
                    "The API key expiration date cannot be in the past",
                    code="invalid_expiry_date",
                )
        return expiry_date
