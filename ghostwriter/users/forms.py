"""This contains all the forms used by the Users application."""

# Django Imports
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import forms, get_user_model
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import ModelForm, ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from allauth.account.forms import LoginForm, SignupForm
from allauth.mfa.base.internal.flows import check_rate_limit
from allauth.mfa.models import Authenticator
from allauth.mfa.adapter import get_adapter
from allauth.mfa.base.forms import AuthenticateForm
from allauth.mfa.totp.forms import ActivateTOTPForm, DeactivateTOTPForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Layout, Row, Submit

User = get_user_model()


class UserChangeForm(UserChangeForm):
    """
    Update details for an individual :model:`users.User`.
    """

    class Meta:
        model = get_user_model()
        fields = (
            "name",
            "timezone",
            "phone",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["autocomplete"] = "off"
        self.fields["phone"].widget.attrs["placeholder"] = "(212) 555-2368"
        self.fields["phone"].help_text = "Work phone number for work contacts"
        self.fields["timezone"].help_text = "Timezone in which you work"
        self.fields["name"].help_text = "Your full name as it should appear in reports"
        self.fields["name"].label = "Your Full Name"
        self.fields["timezone"].label = "Your Timezone"
        self.fields["phone"].label = "Your Contact Number"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-md-12 mb-0"),
                css_class="form-row mt-4",
            ),
            Row(
                Column("phone", css_class="form-group col-md-6 mb-0"),
                Column("timezone", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class UserCreationForm(forms.UserCreationForm):  # pragma: no cover
    """
    Create an individual :model:`users.User`.
    """

    error_message = forms.UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    class Meta(forms.UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise ValidationError(self.error_messages["duplicate_username"])


# Create ModelForm based on the Group model
class GroupAdminForm(ModelForm):
    class Meta:
        model = Group
        exclude = []

    # Add the users field
    users = ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        # Use the pretty ``filter_horizontal`` widget
        widget=FilteredSelectMultiple("users", False),
        label=_(
            "Users",
        ),
    )

    def __init__(self, *args, **kwargs):
        # Do the normal form initialization
        super().__init__(*args, **kwargs)
        # If it is an existing group (saved objects have a pk)
        if self.instance.pk:
            # Populate the users field with the current Group users
            self.fields["users"].initial = self.instance.user_set.all()

    def save_m2m(self):  # pragma: no cover
        # Add the users to the Group
        self.instance.user_set.set(self.cleaned_data["users"])

    def save(self, *args, **kwargs):  # pragma: no cover
        # Default save
        instance = super().save()
        # Save many-to-many data
        self.save_m2m()
        return instance


class UserLoginForm(LoginForm):
    """
    Authenticate an individual :model:`users.User` with their username and password. This is customized
    to make adjustments like disabling autocomplete on the password field.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["login"].widget.attrs["placeholder"] = "Username"
        self.fields["password"].widget.attrs["placeholder"] = "Password"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            Row(
                Column("login", css_class="form-group col-12 mb-0"),
                css_class="form-row mt-4",
            ),
            Row(
                Column("password", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("remember", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
        )


class UserSignupForm(SignupForm):
    """
    Register an individual :model:`users.User` with a username, email, and full name. The resulting user is attached
    to a social login.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["email"].widget.attrs["placeholder"] = "Email Address"
        self.fields["email"].label = "Email Address"
        self.fields["name"].widget.attrs["placeholder"] = "Full Name"
        self.fields["password2"].widget.attrs["placeholder"] = "Repeat Password"
        self.fields["password2"].label = "Password (Again)"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("email", css_class="form-group col-12 mb-0"),
                css_class="form-row mt-4",
            ),
            Row(
                Column("username", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("password1", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("password2", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
        )


class UserMFAAuthenticateForm(AuthenticateForm):
    """
    Authenticate an individual :model:`users.User` with their TOTP. This is customized
    to make adjustments like disabling autocomplete on the token field.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["code"].widget.attrs["placeholder"] = "421 984"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            Row(
                Column("code", css_class="form-group col-4 offset-4 mb-0"),
                css_class="form-row mt-4",
            ),
            ButtonHolder(
                Submit("submit", "Authenticate", css_class="col-4"),
            ),
        )

    def clean_code(self):
        clear_rl = check_rate_limit(self.user)
        code = self.cleaned_data["code"]
        for auth in Authenticator.objects.filter(user=self.user).exclude(
            # WebAuthn cannot validate manual codes.
            type=Authenticator.Type.WEBAUTHN
        ):
            if auth.wrap().validate_code(code):
                self.authenticator = auth
                clear_rl()
                return code

        raise get_adapter().validation_error("incorrect_code")


class UserMFADeviceForm(ActivateTOTPForm):
    """
    Enroll an MFA device for an individual :model:`users.User`. This is customized
    to make adjustments like disabling autocomplete on the token field.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["code"].widget.attrs["placeholder"] = "421 984"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            Row(
                Column("code", css_class="form-group col-4 offset-4 mb-0"),
                css_class="form-row mt-4",
            ),
            ButtonHolder(
                Submit("submit", "Verify", css_class="col-4"),
            ),
        )


class UserMFADeviceRemoveForm(DeactivateTOTPForm):
    """
    Remove an MFA device enrolled for an individual :model:`users.User`. This is customized
    to make adjustments like disabling autocomplete on the password field.
    """

    def __init__(self, *args, **kwargs):
        self.authenticator = kwargs.get("authenticator")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            ButtonHolder(
                Submit("submit", "Disable multi-factor", css_class="col-4"),
            ),
        )

    def clean(self):
        """
        Ensure authenticator is present before proceeding.
        """
        cleaned_data = super().clean()

        if not self.authenticator:
            raise ValidationError("No authenticator device found.")

        return cleaned_data
