"""This contains all the forms used by the Home application."""

# Django Imports
from django import forms
from django.contrib.auth import get_user_model

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Layout, Row, Submit

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
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon avatar-upload-icon">Avatar Upload</h4>
                <hr>
                <div class="offset-md-2 col-md-8 text-justify">
                    <p>Your avatar will be displayed as a circle and automatically cropped to fit. For best results,
                    upload a square image (equal height and width) or ensure your face is centered in the image.</p>
                    <p>Previews for images will appear below.</p>
                </div>
                <div id="avatarPreview" class="pb-3"></div>
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
                    css_class="col-8 offset-md-2",
                )
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
                css_class="mt-3"
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
