"""This contains all of the forms used by the API application."""


# Django Imports
from django import forms

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Layout, Row, Submit


class ApiKeyForm(forms.Form):
    """
    Save an individual :model:`oplog.Oplog`.
    """
    name = forms.CharField()
    expiry_date = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
    )

    class Meta:
        fields = ["name", "expiry_date", ]

    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["expiry_date"].widget.input_type = "datetime-local"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-6 mb-0"),
                Column("expiry_date", css_class="form-group col-6 mb-0"),
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
