"""This contains all the forms used by the Home application."""

# Django Imports
from django import forms
from django.contrib.auth import get_user_model

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, HTML, ButtonHolder, Column, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile


class UserProfileForm(forms.ModelForm):
    """Upload user profile avatar for an individual :model:`home.UserProfile`."""

    class Meta:
        model = UserProfile
        exclude = ("user", "hide_quickstart")
        widgets = {
            "avatar": forms.FileInput(attrs={"class": "custom-file-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["avatar"].label = ""
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_show_labels = False
        self.helper.form_class = "resource-edit-form"
        self.helper.layout = Layout(
            Div(
                HTML(
                    """
                    <div class="profile-avatar-summary">
                      <img class="profile-avatar-current" src="{% url 'users:avatar_download' slug=request.user.username %}" alt="Current profile image">
                      <div>
                        <h1>Profile image</h1>
                        <p>This image appears in navigation, assignments, and activity.</p>
                      </div>
                    </div>
                    <div class="profile-avatar-upload-guidance">
                      <label for="id_avatar">Choose a new image</label>
                      <p>Ghostwriter crops profile images to a circle. Square images with the subject centered work best.</p>
                    </div>
                    """
                ),
                Row(
                    Column(
                        HTML(
                            """
                            {% if form.avatar.errors %}<div class="invalid-feedback d-block">{{ form.avatar.errors }}</div>{% endif %}
                            <div class="custom-file">
                                {{ form.avatar }}
                                <label class="custom-file-label" for="id_avatar" id="filename">
                                    Click here or drag and drop...</label>
                                <script type="text/javascript" id="script-id_avatar">
                                    (function() {
                                        var input = document.getElementById("id_avatar");
                                        var label = document.getElementById("filename");
                                        var placeholder = label.textContent;
                                        if (!input) { console.error("Avatar file input #id_avatar not found"); return; }
                                        input.addEventListener("change", function(e) {
                                            if (e.target.files.length === 0) {
                                                label.textContent = placeholder;
                                            } else {
                                                var filenames = "";
                                                for (var i = 0; i < e.target.files.length; i++) {
                                                    filenames += (i > 0 ? ", " : "") + e.target.files[i].name;
                                                }
                                                label.textContent = filenames;
                                            }
                                        });
                                    })();
                                </script>
                            </div>
                            """
                        ),
                        css_class="col-12",
                    ),
                    css_class="form-row",
                ),
                HTML("""<div id="avatarPreview" class="profile-avatar-preview"></div>"""),
                css_class="resource-form-card profile-avatar-card",
            ),
            Div(
                Div(
                    HTML("""<a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>"""),
                    Submit(
                        "submit",
                        "Save Avatar",
                        css_class="btn btn-primary profile-avatar-submit",
                        disabled=True,
                    ),
                    css_class="resource-form-actions-buttons",
                ),
                css_class="resource-form-actions resource-form-actions-compact",
            ),
        )


class SignupForm(forms.ModelForm):
    """Create a new :model:`users.User`."""

    class Meta:
        model = get_user_model()
        fields = [
            "name",
        ]

    def signup(self, request, user):  # pragma: no cover
        user.name = self.cleaned_data["name"]
        user.save()
