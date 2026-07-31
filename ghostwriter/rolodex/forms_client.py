"""This contains all client-related forms used by the Rolodex application."""

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
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
from ghostwriter.commandcenter.forms import ExtraFieldsField

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import GeneralConfiguration
from ghostwriter.modules.custom_layout_object import CustomTab, Formset, SwitchToggle
from ghostwriter.modules.reportwriter.forms import JinjaRichTextField
from ghostwriter.rolodex.models import Client, ClientContact, ClientInvite, ClientNote

# Number of "extra" formsets created by default
# Higher numbers can increase page load times with WYSIWYG editors
EXTRAS = 0


class BaseClientContactInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ClientContact` that adds validation
    for this model.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        active_forms = []
        contacts = set()
        primary_set = False
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data["DELETE"]:
                continue
            active_forms.append(form)
            name = form.cleaned_data["name"]
            primary = form.cleaned_data["primary"]

            # Check that the same person has not been added more than once
            if name:
                if name in contacts:
                    form.add_error(
                        "name",
                        ValidationError(
                            _("This person is already assigned as a contact."),
                            code="duplicate",
                        ),
                    )
                contacts.add(name)

            if primary:
                if primary_set:
                    form.add_error(
                        "primary",
                        ValidationError(
                            _("You can only set one primary contact."),
                            code="duplicate",
                        ),
                    )
                primary_set = True

        # Auto-set primary when only one contact is being submitted
        if len(active_forms) == 1 and not primary_set:
            active_forms[0].cleaned_data["primary"] = True
            active_forms[0].instance.primary = True
            active_forms[0]._force_primary_save = True
        # Require a primary when multiple contacts exist
        elif len(active_forms) > 1 and not primary_set:
            active_forms[0].add_error(
                "primary",
                ValidationError(
                    _("You must designate one contact as the primary point of contact."),
                    code="required",
                ),
            )
            raise ValidationError(
                _("You must designate one contact as the primary point of contact. You may have marked the primary for deletion. If so, please mark a different contact as primary."),
                code="required",
            )

    def save(self, commit=True):
        instances = super().save(commit=commit)
        if commit:
            for form in self.forms:
                if (
                    getattr(form, "_force_primary_save", False)
                    and form.instance.pk
                    and not form.has_changed()
                    and form not in self.deleted_forms
                ):
                    form.instance.save(update_fields=["primary"])
        else:
            for form in self.forms:
                if (
                    getattr(form, "_force_primary_save", False)
                    and form.instance.pk
                    and form.instance not in instances
                    and form not in self.deleted_forms
                ):
                    instances.append(form.instance)
        return instances


class ClientContactForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ClientContact` associated with an individual
    :model:`rolodex.Client`.
    """

    class Meta:
        model = ClientContact
        exclude = ("client",)
        field_classes = {
            "email": forms.EmailField,
            "description": JinjaRichTextField,
        }

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
        self.fields["description"].widget.attrs["placeholder"] = "Janine is our main contact for assessment work and ..."
        self.fields["description"].widget.attrs["class"] = "gw-tiptap-compact"
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
                HTML(
                    """
                    <details
                        class="collection-form-card"
                        data-collection-item="contact"
                        {% if form.errors or not form.instance.pk %}open{% endif %}
                    >
                        <summary class="collection-form-card-summary">
                            <span class="collection-form-card-icon poc-icon" aria-hidden="true"></span>
                            <span class="collection-form-card-identity">
                                <span class="collection-form-card-title" data-summary-field="name">
                                    Contact details
                                </span>
                                <span class="collection-form-card-meta" data-summary-fields="job_title,email">
                                    Add contact details
                                </span>
                            </span>
                            <span class="collection-form-card-status" data-summary-field="primary"></span>
                            <i class="fas fa-chevron-down collection-form-card-chevron" aria-hidden="true"></i>
                        </summary>
                        <div class="collection-form-card-body">
                    """
                ),
                Div(
                    HTML(
                        """
                        <div class="collection-form-card-heading mb-3">
                            <div>
                                <h3>Contact details</h3>
                                <p>Keep the operator-facing identity and communication details current.</p>
                            </div>
                        </div>
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
                    SwitchToggle("primary", onchange="cbChange(this)", css_class="js-cb-toggle"),
                    "description",
                    Field("DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"),
                    Div(
                        Button(
                            "formset-del-button",
                            "Remove Contact",
                            css_class="btn-outline-danger formset-del-button formset-action-button",
                        ),
                        css_class="formset-actions",
                    ),
                    css_class="formset collection-form-card-fields",
                ),
                HTML("</div></details>"),
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


class ClientInviteForm(forms.ModelForm):
    class Meta:
        model = ClientInvite
        exclude = ("client",)
        field_classes = {
            "comment": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].label = "Operator"
        self.fields["user"].queryset = self.fields["user"].queryset.order_by("-is_active", "username", "name")
        self.fields["user"].label_from_instance = lambda obj: obj.get_display_name
        self.fields["comment"].widget.attrs["class"] = "gw-tiptap-compact"

        self.helper = FormHelper()
        # Disable the <form> tags because this will be part of an instance of `ClientForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>Invite Deleted!</strong>
                        Deletion will be permanent once the form is submitted. Click this alert to undo.
                        """
                    ),
                    css_class="alert alert-danger show formset-undo-button",
                    style="display:none; cursor:pointer;",
                    template="alert.html",
                    block=False,
                    dismiss=False,
                ),
                HTML(
                    """
                    <details
                        class="collection-form-card"
                        data-collection-item="access"
                        {% if form.errors or not form.instance.pk %}open{% endif %}
                    >
                        <summary class="collection-form-card-summary">
                            <span class="collection-form-card-icon users-icon" aria-hidden="true"></span>
                            <span class="collection-form-card-identity">
                                <span class="collection-form-card-title" data-summary-field="user">
                                    Operator access
                                </span>
                                <span class="collection-form-card-meta">Client-level visibility</span>
                            </span>
                            <i class="fas fa-chevron-down collection-form-card-chevron" aria-hidden="true"></i>
                        </summary>
                        <div class="collection-form-card-body">
                    """
                ),
                Div(
                    HTML(
                        """
                        <div class="collection-form-card-heading mb-3">
                            <div>
                                <h3>Access details</h3>
                                <p>Grant an operator visibility into this client and all associated projects.</p>
                            </div>
                        </div>
                        """
                    ),
                    Row(
                        Column("user", css_class="form-group col-md-12"),
                        css_class="form-row",
                    ),
                    "comment",
                    Field("DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"),
                    Div(
                        Button(
                            "formset-del-button",
                            "Remove Access",
                            css_class="btn-outline-danger formset-del-button formset-action-button",
                        ),
                        css_class="formset-actions",
                    ),
                    css_class="formset collection-form-card-fields",
                ),
                HTML("</div></details>"),
                css_class="formset-container"
            )
        )


class BaseClientInviteInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ClientInvite` that adds validation
    for this model.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        invites = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data["DELETE"]:
                continue
            user = form.cleaned_data["user"]

            # Check that the same person has not been added more than once
            if user:
                if user in invites:
                    form.add_error(
                        "user",
                        ValidationError(
                            _("This person is already invited."),
                            code="duplicate",
                        ),
                    )
                invites.add(user)


ClientInviteFormSet = inlineformset_factory(
    Client,
    ClientInvite,
    form=ClientInviteForm,
    formset=BaseClientInviteInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)


class ClientForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.Client` with instances of :model:`rolodex.ClientContact`.
    """

    extra_fields = ExtraFieldsField(Client._meta.label)

    class Meta:
        model = Client
        fields = "__all__"
        field_classes = {
            "description": JinjaRichTextField,
            "address": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        general_config = GeneralConfiguration.get_solo()
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "SpecterOps"
        self.fields["short_name"].widget.attrs["placeholder"] = "Specter"
        self.fields["description"].widget.attrs["placeholder"] = "This client approached us with concerns in these areas ..."
        self.fields["address"].widget.attrs["placeholder"] = "14 N Moore St, New York, NY 10013"
        self.fields["address"].widget.attrs["class"] = "gw-tiptap-compact"
        self.fields["description"].widget.attrs["class"] = "gw-tiptap-narrative"
        self.fields["timezone"].initial = general_config.default_timezone
        self.fields["tags"].widget.attrs["placeholder"] = "cybersecurity, industry:infosec, ..."
        self.fields["description"].label = "Description"
        self.fields["tags"].label = "Tags"
        self.fields["extra_fields"].label = ""

        has_extra_fields = bool(self.fields["extra_fields"].specs)

        tabs = [
            CustomTab(
                "Client Information",
                HTML(
                    """
                    <div class="form-section-heading mb-3">
                        <h2>Identity</h2>
                        <p>Name the client as operators should see it throughout Ghostwriter.</p>
                    </div>
                    """
                ),
                Row(
                    Column("name", css_class="form-group col-md-6 mb-0"),
                    Column("short_name", css_class="form-group col-md-6 mb-0"),
                    css_class="form-row",
                ),
                Row(
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
                        css_class="col-md-6",
                    ),
                    Column("timezone", css_class="form-group col-md-6 mb-0"),
                ),
                "tags",
                HTML(
                    """
                    <div class="form-section-heading mt-2 mb-3">
                        <h2>Client profile</h2>
                        <p>Add the context operators need when planning and reporting work.</p>
                    </div>
                    """
                ),
                Field("logo", wrapper_class="file-field"),
                "address",
                "description",
                link_css_class="client-icon",
                css_id="client",
            ),
            CustomTab(
                "Points of Contact",
                Div(
                    Div(
                        HTML(
                            """
                            <h2>Points of contact</h2>
                            <p>People who coordinate, approve, or receive work for this client.</p>
                            """
                        ),
                        css_class="collection-toolbar-copy",
                    ),
                    Button(
                        "add-contact",
                        "Add Contact",
                        css_class="btn-outline-secondary formset-add-poc",
                    ),
                    css_class="collection-toolbar mb-3",
                ),
                HTML(
                    """
                    <div class="empty-state collection-empty-state{% if contacts.forms %} d-none{% endif %}"
                         data-collection-empty="contact">
                        <i class="fas fa-address-card empty-state-icon" aria-hidden="true"></i>
                        <h3 class="empty-state-title">No contacts yet</h3>
                        <p class="empty-state-description">
                            Add a point of contact when someone coordinates or approves this client's work.
                        </p>
                    </div>
                    """
                ),
                Formset("contacts", object_context_name="Contact"),
                link_css_class="poc-icon",
                css_id="contacts",
            ),
            CustomTab(
                "Access",
                Div(
                    Div(
                        HTML(
                            """
                            <h2>Client access</h2>
                            <p>Operators listed here can view this client and its associated projects.</p>
                            """
                        ),
                        css_class="collection-toolbar-copy",
                    ),
                    Button(
                        "add-invite",
                        "Grant Access",
                        css_class="btn-outline-secondary formset-add-invite",
                    ),
                    css_class="collection-toolbar mb-3",
                ),
                HTML(
                    """
                    <div class="empty-state collection-empty-state{% if invites.forms %} d-none{% endif %}"
                         data-collection-empty="access">
                        <i class="fas fa-user-shield empty-state-icon" aria-hidden="true"></i>
                        <h3 class="empty-state-title">No client-level access</h3>
                        <p class="empty-state-description">
                            Grant access only when an operator needs visibility across this client's work.
                        </p>
                    </div>
                    """
                ),
                Formset("invites", object_context_name="Invite"),
                link_css_class="tab-icon users-icon",
                css_id="invites",
            ),
        ]

        if has_extra_fields:
            tabs.append(
                CustomTab(
                    "Extra Fields",
                    "extra_fields",
                    link_css_class="tab-icon custom-field-icon",
                    css_id="extra-fields",
                )
            )

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            TabHolder(
                *tabs,
                template="tab.html",
                css_class="nav-justified",
                css_id="tab-bar",
            ),
            Div(
                HTML(
                    """
                    <span class="resource-form-actions-context client-form-actions-context">
                        {% if object.pk %}Editing {{ object.name }}{% else %}Creating a new client{% endif %}
                    </span>
                    """
                ),
                Div(
                    HTML(
                        """
                        <a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>
                        """
                    ),
                    Submit(
                        "submit-button",
                        "Save Changes" if self.instance.pk else "Create Client",
                        css_class="btn btn-primary",
                    ),
                    css_class="resource-form-actions-buttons client-form-actions-buttons",
                ),
                css_class="resource-form-actions client-form-actions",
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
