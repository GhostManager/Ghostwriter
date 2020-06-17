"""This contains all of the forms for the Ghostwriter application."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper

from .models import (
    Finding, Report, ReportFindingLink, Evidence, LocalFindingNote,
    FindingNote)

from ghostwriter.rolodex.models import Project

from datetime import datetime


class FindingCreateForm(forms.ModelForm):
    """Form used with the FindingCreate CreateView in views.py to allow
    excluding fields.
    """
    class Meta:
        """Metadata for the model form."""
        model = Finding
        fields = ('__all__')

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(FindingCreateForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = \
            'SQL Injection'
        self.fields['description'].widget.attrs['placeholder'] = \
            'What is this ...'
        self.fields['impact'].widget.attrs['placeholder'] = \
            'What is the impact ...'
        self.fields['mitigation'].widget.attrs['placeholder'] = \
            'What needs to be done ...'
        self.fields['replication_steps'].widget.attrs['placeholder'] = \
            'How to reproduce/find this issue ...'
        self.fields['host_detection_techniques'].\
            widget.attrs['placeholder'] = 'How to detect it on an endpoint ...'
        self.fields['network_detection_techniques'].\
            widget.attrs['placeholder'] = 'How to detect it on a network ...'
        self.fields['references'].widget.attrs['placeholder'] = \
            'Some useful links and references ...'
        self.fields['finding_guidance'].widget.attrs['placeholder'] = \
            'When using this finding in a report be sure to include ...'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'


class ReportCreateForm(forms.ModelForm):
    """Form used with the ReportCreate CreateView in views.py to allow
    excluding fields.
    """
    class Meta:
        """Metadata for the model form."""
        model = Report
        exclude = ('creation', 'last_update',
                   'created_by', 'complete')

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ReportCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class ReportCreateFormStandalone(forms.ModelForm):
    """Form used with the ReportCreateWithoutProject CreateView in views.py
    to allow excluding fields.
    """
    class Meta:
        """Metadata for the model form."""
        model = Report
        exclude = ('creation', 'last_update',
                   'created_by', 'complete')

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ReportCreateFormStandalone, self).__init__(*args, **kwargs)
        active_projects = Project.objects.filter(end_date__gte=datetime.today())
        if active_projects:
            self.fields['project'].empty_label = '-- Select an Active Project --'
        else:
            self.fields['project'].empty_label = '-- No Active Projects --'
        self.fields['project'].queryset = active_projects
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class ReportFindingLinkUpdateForm(forms.ModelForm):
    """Form used with the ReportFindingLink UpdateView in views.py to allow
    excluding fields.
    """
    class Meta:
        """Metadata for the model form."""
        model = ReportFindingLink
        exclude = ('report',)

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ReportFindingLinkUpdateForm, self).__init__(*args, **kwargs)
        # Set a min position of `1`
        self.fields['position'].widget.attrs['min'] = '1'
        # Set placeholder text and other form settings
        self.fields['affected_entities'].widget.attrs['placeholder'] = \
            'DC01.TEXTLAB.LOCAL'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'


class EvidenceForm(forms.ModelForm):
    """Form used with the Evidence model in models.py to allow excluding
    fields.
    """
    class Meta:
        model = Evidence
        fields = ('friendly_name', 'document', 'description',
                  'caption', 'uploaded_by', 'finding')
        widgets = {
                    'uploaded_by': forms.HiddenInput(),
                    'finding': forms.HiddenInput(),
                    'document': forms.FileInput(attrs={'class':
                                                'form-control'})
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(EvidenceForm, self).__init__(*args, **kwargs)
        self.fields['caption'].required = True
        self.fields['friendly_name'].required = True
        self.fields['friendly_name'].widget.attrs['placeholder'] = \
            'BloodHound Graph 1'
        self.fields['caption'].widget.attrs['placeholder'] = \
            'BloodHound graph depicting the first attack path'
        self.fields['description'].widget.attrs['placeholder'] = \
            'This is an annotated BloodHound graph export that shows the ' \
            'first attack path we followed'
        self.fields['document'].label = ''
        self.fields['document'].widget.attrs['class'] = 'custom-file-input'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'

    def clean(self):
        """Clean and sanitize user input."""
        cleaned_data = super(EvidenceForm, self).clean()
        friendly_name = cleaned_data.get('friendly_name')
        finding = cleaned_data.get('finding')
        # Check if provided name has already been used for another file for this report
        report_queryset = Evidence.objects.filter(finding=finding.id).values_list('id', 'friendly_name')
        for evidence in report_queryset:
            if friendly_name == evidence[1] and not self.instance.id == evidence[0]:
                raise ValidationError(_('This friendly name has already been used for a file attached to this finding.'))
        # Return the cleaned data
        return cleaned_data


class FindingNoteCreateForm(forms.ModelForm):
    """Form used with the FindingNote CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = FindingNote
        fields = ('__all__')
        widgets = {
                    'timestamp': forms.HiddenInput(),
                    'operator': forms.HiddenInput(),
                    'finding': forms.HiddenInput(),
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(FindingNoteCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class LocalFindingNoteCreateForm(forms.ModelForm):
    """Form used with the LocalFindingNote CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = LocalFindingNote
        fields = ('__all__')
        widgets = {
                    'timestamp': forms.HiddenInput(),
                    'operator': forms.HiddenInput(),
                    'finding': forms.HiddenInput(),
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(LocalFindingNoteCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False
