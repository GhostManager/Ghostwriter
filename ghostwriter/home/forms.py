"""This contains all of the forms used by the Home application."""

from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.auth import get_user_model

from ghostwriter.home.models import UserProfile


class UserProfileForm(forms.ModelForm):
    """
    Upload user profile avatars for individual :model:`home.UserProfile`.
    """

    class Meta:
        model = UserProfile
        exclude = ("user",)
        widgets = {
            "user": forms.HiddenInput(),
            "avatar": forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields["avatar"].widget.attrs["class"] = "custom-file-input"
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"


class SignupForm(forms.ModelForm):
    """
    Create a new :model:`users.User`.
    """

    class Meta:
        model = get_user_model()
        fields = [
            "name",
        ]

    def signup(self, request, user):
        user.name = self.cleaned_data["name"]
        user.save()
