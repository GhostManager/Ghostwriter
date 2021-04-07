"""This contains all of the forms used by the Users application."""

# Django Imports
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import forms, get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import ModelForm, ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserChangeForm(forms.UserChangeForm):
    """
    Update an individual :model:`users.User`.
    """

    class Meta(forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(forms.UserCreationForm):
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


# Create ModelForm based on the Group model.
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
        # Do the normal form initialisation
        super(GroupAdminForm, self).__init__(*args, **kwargs)
        # If it is an existing group (saved objects have a pk)
        if self.instance.pk:
            # Populate the users field with the current Group users
            self.fields["users"].initial = self.instance.user_set.all()

    def save_m2m(self):
        # Add the users to the Group
        self.instance.user_set.set(self.cleaned_data["users"])

    def save(self, *args, **kwargs):
        # Default save
        instance = super(GroupAdminForm, self).save()
        # Save many-to-many data
        self.save_m2m()
        return instance
