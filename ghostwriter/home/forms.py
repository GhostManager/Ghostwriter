"""This contains all of the forms for the Home application."""

from django import forms
from django.contrib.auth import get_user_model

from crispy_forms.helper import FormHelper

from ghostwriter.home.models import UserProfile


class UserProfileForm(forms.ModelForm):
    """Form used to upload user profile avatars."""
    class Meta:
        """Metadata for the model form."""
        model = UserProfile
        # fields = ('__all__')
        exclude = ('user',)
        widgets = {
            'user': forms.HiddenInput(),
            'avatar': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['avatar'].widget.attrs['class'] = 'custom-file-input'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'


class SignupForm(forms.ModelForm):

    class Meta:
        model = get_user_model()
        fields = ['name', ]

    def signup(self, request, user):
        user.name = self.cleaned_data['name']
        user.save()
