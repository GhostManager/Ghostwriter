from django import forms

from crispy_forms.bootstrap import Alert, TabHolder
from crispy_forms.helper import FormHelper
from ghostwriter.rolodex.models import Project, Client

from .models import Oplog, OplogEntry


class OplogCreateForm(forms.ModelForm):
    """
    Form used with the OplogCreate for creating new oplog entries.
    """
    client_list = forms.ModelChoiceField(queryset=Client.objects.all().order_by('name'))

    class Meta:
        model = Oplog
        fields = ['client_list', 'project', 'name']

    def __init__(self, *args, **kwargs):
        super(OplogCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "newitem"
        self.fields['project'].queryset = Project.objects.none()

        if 'client_list' in self.data:
            try:
                client_id = int(self.data.get('client_list'))
                self.fields['project'].queryset = Project.objects.filter(client=client_id).order_by("name")
            except (ValueError, TypeError):
                pass

        elif self.instance.pk:
            self.fields['project'].queryset = self.instance.client.project_set.order_by("name")


class OplogCreateEntryForm(forms.ModelForm):
    """
    Form used for creating entries in the oplog
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

