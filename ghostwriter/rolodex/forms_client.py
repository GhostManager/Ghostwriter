"""This contains all client-related forms used by the Rolodex application."""

# Standard Libraries
import base64
import io

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
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
from PIL import Image
from ghostwriter.commandcenter.forms import ExtraFieldsField

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import GeneralConfiguration
from ghostwriter.modules.custom_layout_object import CustomTab, Formset
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

        contacts = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data["DELETE"]:
                continue
            name = form.cleaned_data["name"]

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
                    "description",
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
                Div(
                    Row(
                        Column("user", css_class="form-group col-md-12"),
                        css_class="form-row",
                    ),
                    "comment",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Invite",
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
    logo_cover_data = forms.CharField(required=False, widget=forms.HiddenInput())
    logo_header_data = forms.CharField(required=False, widget=forms.HiddenInput())
    logo_source_data = forms.CharField(required=False, widget=forms.HiddenInput())
    logo_cover_scale = forms.IntegerField(required=False, widget=forms.HiddenInput())
    logo_header_scale = forms.IntegerField(required=False, widget=forms.HiddenInput())
    logo_cover_width_px = forms.IntegerField(required=False, widget=forms.HiddenInput())
    logo_cover_height_px = forms.IntegerField(required=False, widget=forms.HiddenInput())
    logo_header_width_px = forms.IntegerField(required=False, widget=forms.HiddenInput())
    logo_header_height_px = forms.IntegerField(required=False, widget=forms.HiddenInput())
    logo_cover_aspect_locked = forms.BooleanField(
        required=False, widget=forms.HiddenInput(), initial=True
    )
    logo_header_aspect_locked = forms.BooleanField(
        required=False, widget=forms.HiddenInput(), initial=True
    )

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
        self.fields["name"].widget.attrs["placeholder"] = "ecfirst"
        self.fields["short_name"].widget.attrs["placeholder"] = "ecfirst"
        note_field = self.fields.get("note")
        if note_field:
            note_field.widget.attrs[
                "placeholder"
            ] = "This client approached us with concerns in these areas ..."
        self.fields["address"].widget.attrs["placeholder"] = "14 N Moore St, New York, NY 10013"
        self.fields["timezone"].initial = general_config.default_timezone
        self.fields["tags"].widget.attrs["placeholder"] = "cybersecurity, industry:infosec, ..."
        self.fields["description"].label = "Description"
        self.fields["tags"].label = "Tags"
        self.fields["extra_fields"].label = ""
        self.fields["logo"].required = False
        self.fields["logo_header"].required = False
        self.fields["logo"].widget = forms.HiddenInput()
        self.fields["logo_header"].widget = forms.HiddenInput()
        # Prevent Django from binding existing file paths back into the hidden inputs
        self.initial["logo"] = None
        self.initial["logo_header"] = None
        self.fields["logo_cover_scale"].initial = 100
        self.fields["logo_header_scale"].initial = 100
        self.fields["logo_cover_width_px"].initial = None
        self.fields["logo_cover_height_px"].initial = None
        self.fields["logo_header_width_px"].initial = None
        self.fields["logo_header_height_px"].initial = None

        def _file_to_data(file_field):
            if not file_field:
                return None, None, None

            try:
                file_field.open("rb")
                content = file_field.read()
            except Exception:
                return None, None, None
            finally:
                try:
                    file_field.close()
                except Exception:
                    pass

            if not content:
                return None, None, None

            mime = getattr(file_field, "file", None)
            mime_type = None
            if mime and hasattr(mime, "content_type"):
                mime_type = mime.content_type
            if not mime_type:
                import mimetypes

                mime_type, _ = mimetypes.guess_type(file_field.name)
            mime_type = mime_type or "image/png"

            data_url = f"data:{mime_type};base64,{base64.b64encode(content).decode('utf-8')}"
            width = height = None
            try:
                with Image.open(io.BytesIO(content)) as img:
                    width, height = img.size
            except Exception:
                pass
            return data_url, width, height

        cover_data_url, cover_width, cover_height = _file_to_data(self.instance.logo)
        header_data_url, header_width, header_height = _file_to_data(
            self.instance.logo_header
        )

        if cover_data_url:
            self.initial.setdefault("logo_cover_data", cover_data_url)
            self.initial.setdefault("logo_source_data", cover_data_url)
            if cover_width and cover_height:
                self.fields["logo_cover_width_px"].initial = cover_width
                self.fields["logo_cover_height_px"].initial = cover_height

        if header_data_url:
            self.initial.setdefault("logo_header_data", header_data_url)
            if not self.initial.get("logo_source_data"):
                self.initial["logo_source_data"] = header_data_url
            if header_width and header_height:
                self.fields["logo_header_width_px"].initial = header_width
                self.fields["logo_header_height_px"].initial = header_height

        has_extra_fields = bool(self.fields["extra_fields"].specs)

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            TabHolder(
                CustomTab(
                    "Client Information",
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
                    Field("logo", wrapper_class="file-field"),
                    "description",
                    HTML(
                        """
                        <h4 class="icon custom-field-icon">Extra Fields</h4>
                        <hr />
                        """
                    ) if has_extra_fields else None,
                    "extra_fields" if has_extra_fields else None,
                    link_css_class="client-icon",
                    css_id="client",
                ),
                CustomTab(
                    "Points of Contact",
                    Formset("contacts", object_context_name="Contact"),
                    Button(
                        "add-contact",
                        "Add Contact",
                        css_class="btn-block btn-secondary formset-add-poc mb-2 offset-4 col-4",
                    ),
                    link_css_class="poc-icon",
                    css_id="contacts",
                ),
                CustomTab(
                    "Logo",
                    Field("logo"),
                    Field("logo_header"),
                    Field("logo_cover_data"),
                    Field("logo_header_data"),
                    Field("logo_source_data"),
                    Field("logo_cover_scale"),
                    Field("logo_header_scale"),
                    Field("logo_cover_width_px"),
                    Field("logo_cover_height_px"),
                    Field("logo_header_width_px"),
                    Field("logo_header_height_px"),
                    Field("logo_cover_aspect_locked"),
                    Field("logo_header_aspect_locked"),
                    HTML(
                        """
                        <div class="mb-3">
                            <button type="button" id="upload-client-logo" class="btn btn-secondary">
                                Upload Client Logo
                            </button>
                            <input
                                type="file"
                                id="client-logo-input"
                                accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,image/svg+xml"
                                style="display: none;"
                            />
                            <p class="text-muted mt-2 mb-0">Supported formats: png, jpg, jpeg, gif, webp, svg</p>
                        </div>
                        <div class="row">
                            <div class="col-md-6">
                                <h5>Cover Page</h5>
                                <canvas id="client-logo-cover" class="border rounded w-100" height="168" aria-label="Cover Page Logo Preview"></canvas>
                                <div class="form-row mt-2">
                                            <div class="form-group col-md-4">
                                                <label class="mb-1" for="cover-width">Width</label>
                                                <div class="input-group">
                                            <input type="number" class="form-control" id="cover-width" min="0.01" step="0.01" value="2" />
                                                    <div class="input-group-append">
                                                        <select id="cover-unit" class="custom-select">
                                                            <option value="in" selected>in</option>
                                                            <option value="px">px</option>
                                                            <option value="cm">cm</option>
                                                    <option value="mm">mm</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                            <div class="form-group col-md-4">
                                                <label class="mb-1" for="cover-height">Height</label>
                                        <input type="number" class="form-control" id="cover-height" min="0.01" step="0.01" value="" />
                                            </div>
                                    <div class="form-group col-md-4 d-flex align-items-end">
                                        <button type="button" id="cover-aspect" class="btn btn-outline-secondary w-100" data-locked="true">
                                            <i class="fas fa-lock"></i> Aspect Locked
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h5>Header</h5>
                                <canvas id="client-logo-header" class="border rounded w-100" height="72" aria-label="Header Logo Preview"></canvas>
                                <div class="form-row mt-2">
                                            <div class="form-group col-md-4">
                                                <label class="mb-1" for="header-width">Width</label>
                                                <div class="input-group">
                                            <input type="number" class="form-control" id="header-width" min="0.01" step="0.01" value="1" />
                                                    <div class="input-group-append">
                                                        <select id="header-unit" class="custom-select">
                                                            <option value="in" selected>in</option>
                                                            <option value="px">px</option>
                                                            <option value="cm">cm</option>
                                                    <option value="mm">mm</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                            <div class="form-group col-md-4">
                                                <label class="mb-1" for="header-height">Height</label>
                                        <input type="number" class="form-control" id="header-height" min="0.01" step="0.01" value="" />
                                            </div>
                                    <div class="form-group col-md-4 d-flex align-items-end">
                                        <button type="button" id="header-aspect" class="btn btn-outline-secondary w-100" data-locked="true">
                                            <i class="fas fa-lock"></i> Aspect Locked
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="mt-3 d-flex justify-content-between align-items-center">
                            <div class="text-muted">Adjust sizes using inches, pixels, or metric units. Unlock the aspect ratio to stretch if needed.</div>
                            <button type="button" id="save-logos" class="btn btn-primary">Save Logo's</button>
                        </div>
                        """
                    ),
                    link_css_class="tab-icon file-icon",
                    css_id="logo",
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

    def _decode_image_bytes(self, data_string):
        if not data_string:
            return None, None

        content_type = "image/png"
        if ";base64," in data_string:
            header, data = data_string.split(";base64,", 1)
            content_type = header.split(":")[-1]
        else:
            data = data_string

        try:
            decoded_file = base64.b64decode(data)
        except (base64.binascii.Error, ValueError):
            return None, None

        if "svg" in content_type:
            try:
                import cairosvg

                decoded_file = cairosvg.svg2png(bytestring=decoded_file)
                content_type = "image/png"
            except Exception:
                return None, None

        return decoded_file, content_type.split("/")[-1]

    def _resample_logo(
        self,
        source_bytes,
        filename_prefix,
        target_width_px=None,
        target_height_px=None,
        max_width=None,
        max_height=None,
        scale_percent=None,
    ):
        if not source_bytes:
            return None

        try:
            with Image.open(io.BytesIO(source_bytes)) as img:
                if not img.width or not img.height:
                    return None
                img = img.convert("RGBA")
                width = target_width_px
                height = target_height_px

                if width and height:
                    width = int(round(width))
                    height = int(round(height))
                else:
                    scale_percent = scale_percent or 100
                    scale_multiplier = scale_percent / 100
                    ratio = 1
                    if max_width and max_height:
                        ratio = min(max_width / img.width, max_height / img.height)
                    width = max(1, int(img.width * ratio * scale_multiplier))
                    height = max(1, int(img.height * ratio * scale_multiplier))

                resized = img.resize((width, height), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                resized.save(buffer, format="PNG", dpi=(300, 300), optimize=True)
                return ContentFile(buffer.getvalue(), name=f"{filename_prefix}.png")
        except Exception:
            return None

    def _save_logo_from_data(self, data_string, filename_prefix):
        decoded_file, file_ext = self._decode_image_bytes(data_string)
        if not decoded_file or not file_ext:
            return None

        return ContentFile(decoded_file, name=f"{filename_prefix}.{file_ext}")

    def save(self, commit=True):
        instance = super().save(commit=False)

        source_bytes, _ = self._decode_image_bytes(self.cleaned_data.get("logo_source_data"))
        cover_scale = self.cleaned_data.get("logo_cover_scale") or 100
        header_scale = self.cleaned_data.get("logo_header_scale") or 100
        cover_width_px = self.cleaned_data.get("logo_cover_width_px")
        cover_height_px = self.cleaned_data.get("logo_cover_height_px")
        header_width_px = self.cleaned_data.get("logo_header_width_px")
        header_height_px = self.cleaned_data.get("logo_header_height_px")

        cover_logo_file = None
        header_logo_file = None

        if source_bytes:
            cover_logo_file = self._resample_logo(
                source_bytes,
                "client_logo_cover",
                target_width_px=cover_width_px,
                target_height_px=cover_height_px,
                max_width=600,
                max_height=1200,
                scale_percent=cover_scale,
            )
            header_logo_file = self._resample_logo(
                source_bytes,
                "client_logo_header",
                target_width_px=header_width_px,
                target_height_px=header_height_px,
                max_width=300,
                max_height=600,
                scale_percent=header_scale,
            )

        if not cover_logo_file:
            cover_logo_file = self._save_logo_from_data(
                self.cleaned_data.get("logo_cover_data"), "client_logo_cover"
            )
        if not header_logo_file:
            header_logo_file = self._save_logo_from_data(
                self.cleaned_data.get("logo_header_data"), "client_logo_header"
            )

        if cover_logo_file:
            instance.logo.save(cover_logo_file.name, cover_logo_file, save=False)
        if header_logo_file:
            instance.logo_header.save(header_logo_file.name, header_logo_file, save=False)

        if commit:
            instance.save()
            self.save_m2m()
        return instance


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
