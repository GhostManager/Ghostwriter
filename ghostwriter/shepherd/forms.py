"""This contains all of the forms for the Shepherd application."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

from datetime import date

from .models import (Domain, History, DomainNote, DomainServerConnection, 
                     DomainStatus)
from .models import (StaticServer, TransientServer, ServerHistory,
                     ServerNote, ServerStatus, AuxServerAddress)
from ghostwriter.rolodex.models import Project


class DateInput(forms.DateInput):
    input_type = 'date'


class CheckoutForm(forms.ModelForm):
    """Form used for domain checkout. Updates the domain (status) and creates
    a history entry.
    """
    class Meta:
        """Modify the attributes of the form."""
        model = History
        fields = ('__all__')
        widgets = {
                    'operator': forms.HiddenInput(),
                    'domain': forms.HiddenInput()
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(CheckoutForm, self).__init__(*args, **kwargs)
        self.fields['client'].empty_label = '-- Select a Client --'
        self.fields['client'].label = ''
        self.fields['activity_type'].empty_label = '-- Select Activity --'
        self.fields['activity_type'].label = ''
        self.fields['project'].empty_label = '-- Select a Client First --'
        self.fields['project'].label = ''
        self.fields['project'].queryset = Project.objects.none()
        self.fields['start_date'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['start_date'].widget.attrs['autocomplete'] = 'off'
        self.fields['end_date'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['end_date'].widget.attrs['autocomplete'] = 'off'
        self.fields['note'].widget.attrs[
            'placeholder'] = 'This domain will be used for...'
        self.fields['note'].label = ''
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        # Prevent "not one of the valid options" errors from AJAX project
        # filtering
        if 'client' in self.data:
            try:
                client_id = int(self.data.get('client'))
                self.fields['project'].queryset = Project.objects.\
                    filter(client_id=client_id).order_by('codename')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['project'].queryset = \
                self.instance.client.project_set.order_by('codename')

    def clean_end_date(self):
        """Clean and sanitize user input."""
        end_date = self.cleaned_data['end_date']
        start_date = self.cleaned_data['start_date']
        # Check if end_date comes before the start_date
        if end_date < start_date:
            raise ValidationError(_('Invalid date: The provided end date '
                                    'comes before the start date.'))
        # Return the cleaned data
        return end_date

    def clean_domain(self):
        insert = self.instance.pk == None
        domain = self.cleaned_data['domain']
        if insert:
            unavailable = DomainStatus.objects.get(domain_status='Unavailable')
            expired = domain.expiration < date.today()
            if expired:
                raise ValidationError("This domain's registration has expired!")
            if domain.domain_status == unavailable:
                raise ValidationError('Someone beat you to it. This domain has '
                                      'already been checked out!')
        # Return the cleaned data
        return domain


class ServerCheckoutForm(forms.ModelForm):
    """Form used for server checkout. Updates the server (status) and creates
    a history entry.
    """
    class Meta:
        """Modify the attributes of the form."""
        model = ServerHistory
        fields = ('__all__')
        widgets = {
                    'operator': forms.HiddenInput(),
                    'server': forms.HiddenInput()
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ServerCheckoutForm, self).__init__(*args, **kwargs)
        self.fields['client'].empty_label = '-- Select a Client --'
        self.fields['client'].label = ''
        self.fields['activity_type'].empty_label = '-- Select Activity --'
        self.fields['activity_type'].label = ''
        self.fields['server_role'].empty_label = '-- Select Role --'
        self.fields['server_role'].label = ''
        self.fields['project'].empty_label = '-- Select a Client First --'
        self.fields['project'].label = ''
        self.fields['project'].queryset = Project.objects.none()
        self.fields['start_date'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['start_date'].widget.attrs['autocomplete'] = 'off'
        self.fields['end_date'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['end_date'].widget.attrs['autocomplete'] = 'off'
        self.fields['note'].widget.attrs[
            'placeholder'] = 'This server will be used for C2 with ...'
        self.fields['note'].label = ''
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        # Prevent "not one of the valid options" errors from AJAX project
        # filtering
        if 'client' in self.data:
            try:
                client_id = int(self.data.get('client'))
                self.fields['project'].queryset = Project.objects.\
                    filter(client_id=client_id).order_by('codename')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['project'].queryset = \
                self.instance.client.project_set.order_by('codename')

    def clean_end_date(self):
        """Clean and sanitize user input."""
        end_date = self.cleaned_data['end_date']
        start_date = self.cleaned_data['start_date']
        # Check if end_date comes before the start_date
        if end_date < start_date:
            raise ValidationError(_('Invalid date: The provided end date '
                                    'comes before the start date.'))
        # Return the cleaned data
        return end_date

    def clean_server(self):
        insert = self.instance.pk == None
        server = self.cleaned_data['server']
        if insert:
            unavailable = ServerStatus.objects.get(server_status='Unavailable')
            if server.server_status == unavailable:
                raise ValidationError('Someone beat you to it. This server has '
                                      'already been checked out!')
        # Return the cleaned data
        return server


class DomainCreateForm(forms.ModelForm):
    """Form used with the DomainCreate CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = Domain
        exclude = ('last_used_by', 'burned_explanation', 'all_cat',
                   'dns_record', 'health_dns', 'expired')

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(DomainCreateForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = 'specterops.io'
        self.fields['name'].label = ''
        self.fields['registrar'].widget.attrs['placeholder'] = 'Namecheap'
        self.fields['registrar'].label = ''
        self.fields['creation'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['domain_status'].empty_label = '-- Select Status --'
        self.fields['domain_status'].label = ''
        self.fields['whois_status'].empty_label = '-- Select Status --'
        self.fields['whois_status'].label = ''
        self.fields['health_status'].empty_label = '-- Select Status --'
        self.fields['health_status'].label = ''
        self.fields['creation'].widget.attrs['autocomplete'] = 'off'
        self.fields['expiration'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['expiration'].widget.attrs['autocomplete'] = 'off'
        self.fields['bluecoat_cat'].widget.attrs[
            'placeholder'] = 'Category A, Category B, ...'
        self.fields['fortiguard_cat'].widget.attrs[
            'placeholder'] = 'Category A, Category B, ...'
        self.fields['ibm_xforce_cat'].widget.attrs[
            'placeholder'] = 'Category A, Category B, ...'
        self.fields['opendns_cat'].widget.attrs[
            'placeholder'] = 'Category A, Category B, ...'
        self.fields['talos_cat'].widget.attrs[
            'placeholder'] = 'Category A, Category B, ...'
        self.fields['trendmicro_cat'].widget.attrs[
            'placeholder'] = 'Category A, Category B, ...'
        self.fields['mx_toolbox_status'].widget.attrs[
            'placeholder'] = 'Spamhaus Blacklist ...'
        self.fields['note'].widget.attrs['placeholder'] = \
            'This domain is an effective lookalike of populardomain.tld ...'
        self.fields['note'].label = ''
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'

    def clean_expiration(self):
        """Clean and sanitize user input."""
        expiration = self.cleaned_data['expiration']
        creation = self.cleaned_data['creation']
        # Check if expiration comes before the creation date
        if expiration < creation:
            raise ValidationError(_('Invalid date: The provided expiration '
                                    'date comes before the purchase date.'))
        # Return the cleaned data
        return expiration


class ServerCreateForm(forms.ModelForm):
    """Form used with the ServerCreate CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = StaticServer
        exclude = ('last_used_by',)

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ServerCreateForm, self).__init__(*args, **kwargs)
        self.fields['ip_address'].widget.attrs['placeholder'] = '172.10.10.236'
        self.fields['name'].widget.attrs['placeholder'] = 'hostname'
        self.fields['server_status'].empty_label = '-- Select Status --'
        self.fields['server_provider'].empty_label = '-- Select Provider --'
        self.fields['note'].widget.attrs[
            'placeholder'] = 'The server lives in the data center...'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class TransientServerCreateForm(forms.ModelForm):
    """Form used with the TransientServer CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = TransientServer
        fields = ('__all__')
        widgets = {
                    'operator': forms.HiddenInput(),
                    'project': forms.HiddenInput()
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(TransientServerCreateForm, self).__init__(*args, **kwargs)
        self.fields['ip_address'].widget.attrs['placeholder'] = '172.10.10.236'
        self.fields['name'].widget.attrs['placeholder'] = 'hostname'
        self.fields['activity_type'].empty_label = '-- Select Activity --'
        self.fields['server_role'].empty_label = '-- Select Role --'
        self.fields['server_provider'].empty_label = '-- Select Provider --'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class DomainLinkForm(forms.ModelForm):
    """Form used with the DomainLServerConnection views."""
    class Meta:
        """Modify the attributes of the form."""
        model = DomainServerConnection
        fields = ('__all__')
        widgets = {
                    'project': forms.HiddenInput(),
                  }

    def __init__(self, project=None, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(DomainLinkForm, self).__init__(*args, **kwargs)
        if project:
            self.fields['domain'].queryset = History.objects.\
                filter(project=project)
            self.fields['domain'].empty_label = \
                '-- Select a Domain [Required] --'
            self.fields['static_server'].queryset = ServerHistory.objects.\
                filter(project=project)
            self.fields['static_server'].empty_label = \
                '-- Select Static Server --'
            self.fields['transient_server'].queryset = TransientServer.\
                objects.filter(project=project)
            self.fields['transient_server'].empty_label = '-- Select VPS --'
            self.helper = FormHelper()
            self.helper.form_class = 'form-inline'
            self.helper.form_method = 'post'
            self.helper.field_class = \
                'h-100 justify-content-center align-items-center'

    def clean(self):
        """Clean and sanitize user input."""
        if (
            self.cleaned_data['static_server'] and
            self.cleaned_data['transient_server']
           ):
            raise ValidationError(_('Invalid Server Selection: Select only '
                                    'one server'))
        if (
            not self.cleaned_data['static_server'] and
            not self.cleaned_data['transient_server']
           ):
            raise ValidationError(_('Invalid Server Selection: You must '
                                    'select one server'))


class DomainNoteCreateForm(forms.ModelForm):
    """Form used with the DomainNote CreateView in views..py."""
    class Meta:
        """Modify the attributes of the form."""
        model = DomainNote
        fields = ('__all__')
        widgets = {
                    'timestamp': forms.HiddenInput(),
                    'operator': forms.HiddenInput(),
                    'domain': forms.HiddenInput(),
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(DomainNoteCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class ServerNoteCreateForm(forms.ModelForm):
    """Form used with the ServerNote CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = ServerNote
        fields = ('__all__')
        widgets = {
                    'timestamp': forms.HiddenInput(),
                    'operator': forms.HiddenInput(),
                    'server': forms.HiddenInput(),
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ServerNoteCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class BurnForm(forms.ModelForm):
    """Form used with the `burn` in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = Domain
        fields = ('burned_explanation',)

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(BurnForm, self).__init__(*args, **kwargs)
        self.fields['burned_explanation'].widget.attrs['placeholder'] = \
            'This domain was flagged for spam after being used for phishing...'
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.helper.form_show_labels = False


class AuxServerAddressCreateForm(forms.ModelForm):
    """Form used with the AuxAddress CreateView in views.py."""
    class Meta:
        """Modify the attributes of the form."""
        model = AuxServerAddress
        fields = ('__all__')
        widgets = {
                    'static_server': forms.HiddenInput(),
                  }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(AuxServerAddressCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'post'
        self.helper.field_class = \
            'h-100 justify-content-center align-items-center'
        self.fields['primary'].label = 'Make Primary Address'
        self.fields['ip_address'].label = ''