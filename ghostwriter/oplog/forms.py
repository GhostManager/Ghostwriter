"""This contains all of the forms used by the Oplog application."""


from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Layout,
    Submit,
)
from django import forms

# Ghostwriter Libraries
from ghostwriter.rolodex.models import Project

from .models import Oplog, OplogEntry


class OplogForm(forms.ModelForm):
    """
    Save an individual :model:`oplog.Oplog`.
    """

    class Meta:
        model = Oplog
        fields = "__all__"

    def __init__(self, project=None, *args, **kwargs):
        super(OplogForm, self).__init__(*args, **kwargs)
        self.project_instance = project
        # Limit the list to just projects not marked as complete
        active_projects = Project.objects.filter(complete=False)
        if active_projects:
            self.fields["project"].empty_label = "-- Select an Active Project --"
        else:
            self.fields["project"].empty_label = "-- No Active Projects --"
        self.fields["project"].queryset = active_projects
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.layout = Layout(
            "name",
            "project",
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class OplogEntryForm(forms.ModelForm):
    """
    Save an individual :model:`oplog.OplogEntry`.
    """

    class Meta:
        model = OplogEntry
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(OplogEntryForm, self).__init__(*args, **kwargs)
        # self.oplog_id = pk
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"
