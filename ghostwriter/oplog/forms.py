"""This contains all of the forms used by the Oplog application."""

# Django & Other 3rd Party Libraries
from crispy_forms.helper import FormHelper
from django import forms

from .models import Oplog, OplogEntry


class OplogCreateForm(forms.ModelForm):
    """
    Save an individual :model:`oplog.Oplog`.
    """

    class Meta:
        model = Oplog
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(OplogCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"


class OplogCreateEntryForm(forms.ModelForm):
    """
    Save an individual :model:`oplog.OplogEntry`.
    """

    class Meta:
        model = OplogEntry
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(OplogCreateEntryForm, self).__init__(*args, **kwargs)
        # self.oplog_id = pk
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"
