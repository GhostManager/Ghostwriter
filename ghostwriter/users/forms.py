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
from allauth.account.forms import LoginForm
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
            "email",
            "name",
            "timezone",
            "phone",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].widget.attrs["autocomplete"] = "off"
        self.fields["phone"].widget.attrs["placeholder"] = "Your Work Number"
        self.fields["phone"].help_text = "Work phone number for work contacts"
        self.fields["timezone"].help_text = "Timezone in which you work"
        self.fields["name"].label = "Your Full Name"
        self.fields["email"].label = "Your Primary Email Address"
        self.fields["timezone"].label = "Your Timezone"
        self.fields["phone"].label = "Your Contact Number"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-md-6 mb-0"),
                Column("email", css_class="form-group col-md-6 mb-0"),
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
        self.helper.layout = Layout(
            Row(
                Column("login", css_class="form-group col-12 mb-0"),
                css_class="form-row mt-4",
            ),
            Row(
                Column("password", css_class="form-group col-12 mb-0"),
                css_class="form-row",
            ),
        )
