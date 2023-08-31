"""This contains all client-related forms used by the Rolodex application."""

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.bootstrap import Alert, FieldWithButtons, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    Button,
    ButtonHolder,
    Column,
    Div,
    Field,
    Layout,
    Row,
    Submit,
)

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import GeneralConfiguration
from ghostwriter.modules.custom_layout_object import CustomTab, Formset
from ghostwriter.rolodex.models import Client, ClientContact, ClientNote

# Number of "extra" formsets created by default
# Higher numbers can increase page load times with WYSIWYG editors
EXTRAS = 0


class BaseClientContactInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ClientContact` that adds validation
    for this model.
    """

    def clean(self):
        contacts = []
        duplicates = False
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
                    name = form.cleaned_data["name"]
                    job_title = form.cleaned_data["job_title"]
                    email = form.cleaned_data["email"]

                    # Check that the same person has not been added more than once
                    if name:
                        if name in contacts:
                            duplicates = True
                        contacts.append(name)
                    if duplicates:
                        form.add_error(
                            "name",
                            ValidationError(
                                _("This person is already assigned as a contact."),
                                code="duplicate",
                            ),
                        )
                    # Raise an error if a name is provided without any required details
                    if name and any(x is None for x in [job_title, email]):
                        if not job_title:
                            form.add_error(
                                "job_title",
                                ValidationError(
                                    _("This person is missing a job title / role."),
                                    code="incomplete",
                                ),
                            )
                        if not email:
                            form.add_error(
                                "email",
                                ValidationError(
                                    _("This person is missing an email address."),
                                    code="incomplete",
                                ),
                            )
                    # Check that the email address is in a valid format
                    if email:
                        try:
                            validate_email(email)
                        except ValidationError:
                            form.add_error(
                                "email",
                                ValidationError(
                                    _("Enter a valid email address for this contact."),
                                    code="invalid",
                                ),
                            )


class ClientContactForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ClientContact` associated with an individual
    :model:`rolodex.Client`.
    """

    class Meta:
        model = ClientContact
        exclude = ("client",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        general_config = GeneralConfiguration.get_solo()
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "Janine Melnitz"
        self.fields["name"].label = "Full Name"
        self.fields["email"].widget.attrs["placeholder"] = "info@getghostwriter.io"
        self.fields["email"].label = "Email Address"
        self.fields["job_title"].widget.attrs["placeholder"] = "COO"
        self.fields["phone"].widget.attrs["placeholder"] = "(212) 897-1964"
        self.fields["phone"].label = "Phone Number"
        self.fields["note"].widget.attrs["placeholder"] = "Janine is our main contact for assessment work and ..."
        self.fields["timezone"].initial = general_config.default_timezone
        self.helper = FormHelper()
        # Disable the <form> tags because this will be part of an instance of `ClientForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            # Wrap form in a div so Django renders form instances in their own element
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>Contact Deleted!</strong>
                        Deletion will be permanent once the form is submitted. Click this alert to undo.
                        """
                    ),
                    css_class="alert alert-danger show formset-undo-button",
                    style="display:none; cursor:pointer;",
                    template="alert.html",
                    block=False,
                    dismiss=False,
                ),
                Div(
                    HTML(
                        """
                        <h6>Contact #<span class="counter">{{ forloop.counter }}</span></h6>
                        <hr>
                        """
                    ),
                    Row(
                        Column("name", css_class="form-group col-md-6 mb-0"),
                        Column("job_title", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("email", css_class="form-group col-md-4 mb-0"),
                        Column("phone", css_class="form-group col-md-4 mb-0"),
                        Column("timezone", css_class="form-group col-md-4 mb-0"),
                        css_class="form-row",
                    ),
                    "note",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Contact",
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


# Create the ``inlineformset_factory()`` objects for ``ClientForm()``

ClientContactFormSet = inlineformset_factory(
    Client,
    ClientContact,
    form=ClientContactForm,
    formset=BaseClientContactInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)


class ClientForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.Client` with instances of :model:`rolodex.ClientContact`.
    """

    class Meta:
        model = Client
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        general_config = GeneralConfiguration.get_solo()
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "SpecterOps"
        self.fields["short_name"].widget.attrs["placeholder"] = "Specter"
        self.fields["note"].widget.attrs["placeholder"] = "This client approached us with concerns in these areas ..."
        self.fields["address"].widget.attrs["placeholder"] = "14 N Moore St, New York, NY 10013"
        self.fields["timezone"].initial = general_config.default_timezone
        self.fields["tags"].widget.attrs["placeholder"] = "cybersecurity, industry:infosec, ..."
        self.fields["note"].label = "Notes"
        self.fields["tags"].label = "Tags"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            TabHolder(
                CustomTab(
                    "Client Information",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Row(
                        Column("name", css_class="form-group col-md-6 mb-0"),
                        Column("short_name", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("tags", css_class="form-group col-md-4 mb-0"),
                        Column(
                            FieldWithButtons(
                                "codename",
                                HTML(
                                    """
                                    <button
                                        class="btn btn-secondary js-roll-codename"
                                        roll-codename-url="{% url 'rolodex:ajax_roll_codename' %}"
                                        type="button"
                                    >
                                    <i class="fas fa-dice"></i>
                                    </button>
                                    """
                                ),
                            ),
                            css_class="col-md-4",
                        ),
                        Column("timezone", css_class="form-group col-md-4 mb-0"),
                    ),
                    "address",
                    "note",
                    link_css_class="client-icon",
                    css_id="client",
                ),
                CustomTab(
                    "Points of Contact",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Formset("contacts", object_context_name="Contact"),
                    Button(
                        "add-contact",
                        "Add Contact",
                        css_class="btn-block btn-secondary formset-add-poc",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    link_css_class="poc-icon",
                    css_id="contacts",
                ),
                template="tab.html",
                css_class="nav-justified",
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class ClientNoteForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ClientNote` associated with an individual
    :model:`rolodex.Client`.
    """

    class Meta:
        model = ClientNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div("note"),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean_note(self):
        note = self.cleaned_data["note"]
        # Check if note is empty
        if not note:
            raise ValidationError(
                _("You must provide some content for the note."),
                code="required",
            )
        return note
