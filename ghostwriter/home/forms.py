"""This contains all of the forms used by the Home application."""

# Django Imports
from django import forms
from django.contrib.auth import get_user_model

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Layout, Submit

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile


class UserProfileForm(forms.ModelForm):
    """
    Upload user profile avatars for individual :model:`home.UserProfile`.
    """

    class Meta:
        model = UserProfile
        exclude = ("user",)
        widgets = {
            "avatar": forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields["avatar"].label = ""
        self.fields["avatar"].widget.attrs["class"] = "custom-file-input"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon avatar-upload-icon">Avatar Upload</h4>
                """
            ),
            Div(
                "avatar",
                HTML(
                    """
                    <label id="filename" class="custom-file-label" for="customFile">Choose an Avatar Image File...</label>
                    """
                ),
                css_class="custom-file",
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
