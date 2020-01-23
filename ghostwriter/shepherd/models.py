"""This contains all of the database models for the Shepherd application."""

from django.db import models
from django.urls import reverse
# from django.contrib.auth.models import User
from django.conf import settings

import datetime
from datetime import date


class HealthStatus(models.Model):
    """Model representing the available domain health statuses."""
    health_status = models.CharField(
        max_length=20,
        unique=True,
        help_text='Health status type (e.g. Healthy, Burned)')

    def count_status(self):
        """Count and return the number of domains using the status entry in
        the `Domain` model.
        """
        return Domain.objects.filter(health_status=self).count()

    count = property(count_status)

    class Meta:
        """Metadata for the model."""
        ordering = ['health_status']
        verbose_name = 'Health status'
        verbose_name_plural = 'Health statuses'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.health_status


class DomainStatus(models.Model):
    """Model representing the available domain statuses."""
    domain_status = models.CharField(
        max_length=20,
        unique=True,
        help_text='Domain status type (e.g. Available)')

    def count_status(self):
        """Count and return the number of domains using the status entry in
        the `Domain` model.
        """
        return Domain.objects.filter(domain_status=self).count()

    count = property(count_status)

    class Meta:
        """Metadata for the model."""
        ordering = ['domain_status']
        verbose_name = 'Domain status'
        verbose_name_plural = 'Domain statuses'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.domain_status


class WhoisStatus(models.Model):
    """Model representing the available WHOIS privacy statuses."""
    whois_status = models.CharField(
        max_length=20,
        unique=True,
        help_text='WHOIS privacy status (e.g. Enabled, Disabled)')

    def count_status(self):
        """Count and return the number of domains using the status entry in
        the `Domain` model."""
        return Domain.objects.filter(whois_status=self).count()

    count = property(whois_status)

    class Meta:
        """Metadata for the model."""
        ordering = ['whois_status']
        verbose_name = 'WHOIS status'
        verbose_name_plural = 'WHOIS statuses'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.whois_status


class ActivityType(models.Model):
    """Model representing the available activity types for domains and
    servers.
    """
    activity = models.CharField(
        max_length=100,
        unique=True,
        help_text='Reason for the use of the asset (e.g. C2, Phishing)')

    class Meta:
        """Metadata for the model."""
        ordering = ['activity']
        verbose_name = 'Activity type'
        verbose_name_plural = 'Activity types'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.activity


class Domain(models.Model):
    """Model representing domains and their related information. This is one
    of the primary models for the Shepherd application. This model keeps a
    record of the domain name and the domain's health, categories, and
    current status (e.g. Available).

    There are foreign keys for the `WhoisStatus`, `HealthStatus`,
    `DomainStatus`, and `User` models.
    """
    name = models.CharField(
        'Name', max_length=100, unique=True, help_text='Enter the domain name')
    registrar = models.CharField(
        'Registrar',
        max_length=100,
        null=True,
        blank=True,
        help_text='Enter the name of the registrar where this domain is '
                  'registered')
    dns_record = models.CharField(
        'DNS Records',
        max_length=500,
        null=True,
        blank=True,
        help_text='Enter the domain\'s DNS records - leave blank if you '
                  'would prefer to let Ghostwriter fill this in later')
    health_dns = models.CharField(
        'DNS Health',
        max_length=100,
        null=True,
        blank=True,
        help_text='Enter passive DNS information from VirusTotal - leave '
                  'blank or enter "Healthy" if you do not know')
    creation = models.DateField(
        'Purchase Date',
        help_text='Select the date the domain was purchased')
    expiration = models.DateField(
        'Expiration Date',
        help_text='Select the date the domain will expire')
    all_cat = models.TextField(
        'All Categories',
        null=True,
        blank=True,
        help_text='Enter all categories applied to this domain')
    ibm_xforce_cat = models.CharField(
        'IBM X-Force',
        max_length=100,
        null=True,
        blank=True,
        help_text='Provide the list of categories determined by IBM X-Force')
    talos_cat = models.CharField(
        'Cisco Talos',
        max_length=100,
        null=True,
        blank=True,
        help_text='Provide the list of categories determined by Cisco Talos')
    bluecoat_cat = models.CharField(
        'Bluecoat',
        max_length=100,
        null=True,
        blank=True,
        help_text='Provide the list of categories determined by Bluecoat')
    fortiguard_cat = models.CharField(
        'Fortiguard',
        max_length=100,
        null=True,
        blank=True,
        help_text='Provide the list of categories determined by Fortiguard')
    opendns_cat = models.CharField(
        'OpenDNS',
        max_length=100,
        null=True,
        blank=True,
        help_text='Provide the list of categories determined by OpenDNS')
    trendmicro_cat = models.CharField(
        'TrendMicro',
        max_length=100,
        null=True,
        blank=True,
        help_text='Provide the list of categories determined by TrendMicro')
    mx_toolbox_status = models.CharField(
        'MX Toolbox Status',
        max_length=100,
        null=True,
        blank=True,
        help_text='Enter the domain spam/blacklist status as determined '
                  'by MX Toolbox')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to provide notes and thoughts behind its '
                  'purchase and intended use')
    burned_explanation = models.TextField(
        'Health Explanation',
        null=True,
        blank=True,
        help_text='Include details such as how the domain was detected, why '
                  'it was blacklisted for spam, if it was flagged with a bad '
                  'category, etc.')
    auto_renew = models.BooleanField(
        'Auto Renew',
        default=True,
        help_text='Whether or not the domain is set to renew automatically '
                  'with the registrar'
    )
    expired = models.BooleanField(
        'Expiration Status',
        default=False,
        help_text='Whether or not the domain registration has expired'
    )
    # Foreign Keys
    whois_status = models.ForeignKey(
        'WhoisStatus',
        on_delete=models.PROTECT,
        null=True,
        default=1,
        help_text='The domain\'s WHOIS privacy status - you want this to be '
                  'Enabled with your registrar')
    health_status = models.ForeignKey(
        'HealthStatus',
        on_delete=models.PROTECT,
        null=True,
        default=1,
        help_text='The domain\'s current health status - set to Healthy if '
                  'you are not sure and assumed the domain is ready to be '
                  'used')
    domain_status = models.ForeignKey(
        'DomainStatus',
        on_delete=models.PROTECT,
        null=True,
        default=1,
        help_text='The domain\'s current status - set to Available in most '
                  'cases, or set to Reserved if it should not be used yet')
    last_used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='The last user to checkout this domain')

    class Meta:
        """Metadata for the model."""
        ordering = ['health_status', 'name', 'expiration']
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('shepherd:domain_detail', args=[str(self.id)])

    def get_domain_age(self):
        """Calculate the domain's age based on the current date and the
        domain's purchase date.
        """
        time_delta = datetime.date.today() - self.creation
        return '{} days'.format(time_delta.days)

    def is_expired(self):
        """Check if the domain's expiration date is in the past."""
        expired = False
        if datetime.date.today() > self.expiration:
            if not self.auto_renew:
                expired = True
        return expired

    @property
    def get_list(self):
        """Property to enable fetching the list from the dns_record entry."""
        if self.dns_record:
            return self.dns_record.split(' ::: ')
        else:
            None

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.name} ({self.health_status})'


class History(models.Model):
    """Model representing the project history for a domain. This model records
    start and end dates
    for a domain checkout period.

    There are foreign keys for the `Client`, `Domain`, `User`, `Project`, and
    `ActivityType` models.
    """
    start_date = models.DateField(
        'Start Date',
        max_length=100,
        help_text='Select the start date of the project')
    end_date = models.DateField(
        'End Date',
        max_length=100,
        help_text='Select the end date of the project')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to provide project-related notes, such as '
                  'how the domain will be used/how it worked out')
    # Foreign Keys
    domain = models.ForeignKey(
        'Domain',
        on_delete=models.CASCADE,
        null=False,
        help_text='Select the domain you wish to check-out')
    client = models.ForeignKey(
        'rolodex.Client',
        on_delete=models.CASCADE,
        null=False,
        help_text='Select the client associated with this checkout')
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE,
        null=True,
        help_text='Select the project associated with the checkout - this '
                  'field will populate after you select a client above')
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Select the user checking out this domain')
    activity_type = models.ForeignKey(
        'ActivityType',
        on_delete=models.PROTECT,
        null=False,
        help_text='Select the intended use of this domain')

    class Meta:
        """Metadata for the model."""
        ordering = ['client', 'domain', 'activity_type', 'start_date']
        verbose_name = 'Domain history'
        verbose_name_plural = 'Domain history'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('shepherd:history_update', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.project} : {self.domain.name}'

    @property
    def will_be_released(self):
        """Property to test if the provided end date within 24-48 hours."""
        if (
            date.today() == self.end_date or
            date.today() == datetime.timedelta(days=1) or
            date.today() > self.end_date
        ):
            return True
        return False


class ServerStatus(models.Model):
    """Model representing the available server statuses."""
    server_status = models.CharField(
        max_length=20,
        unique=True,
        help_text='Server status (e.g. Available)')

    def count_status(self):
        """Count and return the number of servers using the status entry in
        the `Server` model.
        """
        return StaticServer.objects.filter(server_status=self).count()

    count = property(count_status)

    class Meta:
        """Metadata for the model."""
        ordering = ['server_status']
        verbose_name = 'Server status'
        verbose_name_plural = 'Server statuses'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.server_status


class ServerProvider(models.Model):
    """Model representing the available server providers."""
    server_provider = models.CharField(
        max_length=100,
        unique=True,
        help_text='Name of the server provider (e.g. Amazon Web '
                  'Services, Azure)')

    def count_provider(self):
        """Count and return the number of servers using the  entry in the
        `Server` model.
        """
        return StaticServer.objects.filter(server_provider=self).count()

    count = property(count_provider)

    class Meta:
        """Metadata for the model."""
        ordering = ['server_provider']
        verbose_name = 'Server provider'
        verbose_name_plural = 'Server providers'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.server_provider


class StaticServer(models.Model):
    """Model representing servers and related information. This is one of the
    primary models for the Shepherd application. This model keeps a record of
    the server IP addresses, current status (e.g. Available), and who used it
    last.

    There are foreign keys for the `User`, `ServerStatus`, and
    `ServerProvider` models.
    """
    ip_address = models.GenericIPAddressField(
        'IP Address',
        max_length=100,
        unique=True,
        help_text='Enter the server\'s static IP address')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to provide server-related notes, such as '
                  'its designated use or how it can be used')
    name = models.CharField(
        'Name',
        max_length=100,
        null=True,
        blank=True,
        help_text='Enter the server\'s name (typically hostname)')

    # Foreign Keys
    server_status = models.ForeignKey(
        ServerStatus,
        on_delete=models.PROTECT,
        null=True,
        help_text='Enter the server\'s current status - typically Available '
                  'unless it needs to be set aside immediately upon creation')
    server_provider = models.ForeignKey(
        ServerProvider,
        on_delete=models.PROTECT,
        null=True,
        help_text='Select the service provider for this server')
    last_used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['server_status', 'server_provider', 'ip_address']
        verbose_name = 'Static server'
        verbose_name_plural = 'Static servers'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('shepherd:server_detail', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.ip_address} ({self.name}) [{self.server_provider}]'


class ServerRole(models.Model):
    """Model representing the available server roles."""
    server_role = models.CharField(
        max_length=100,
        unique=True,
        help_text='A role for applied to the use of a server '
                  '(e.g. Payload Delivery, Redirector)')

    class Meta:
        """Metadata for the model."""
        ordering = ['server_role']
        verbose_name = 'Server role'
        verbose_name_plural = 'Server roles'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.server_role


class ServerHistory(models.Model):
    """Model representing the project history for servers. This model records
    start and end dates for a server checkout period.

    There are foreign keys for the `Client`, `Server`, `User`, `Project`,
    `ActivityType`, and `ServerRole` models.
    """
    start_date = models.DateField(
        'Start Date',
        max_length=100,
        help_text='Select the start date of the project')
    end_date = models.DateField(
        'End Date',
        max_length=100,
        help_text='Select the end date of the project')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to provide project-related notes, such as '
                  'how the server/IP will be used')
    # Foreign Keys
    server = models.ForeignKey(
        'StaticServer',
        on_delete=models.CASCADE,
        null=False,
        help_text='Select the server being checked out')
    client = models.ForeignKey(
        'rolodex.Client',
        on_delete=models.CASCADE,
        null=False,
        help_text='Select the client associated with the checkout')
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE,
        null=True,
        help_text='Select the project associated with the checkout - this '
                  'field will populate after you select a client above')
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Select the user associated with this checkout')
    server_role = models.ForeignKey(
        'ServerRole',
        on_delete=models.PROTECT,
        null=False,
        help_text='Select the intended role the server will play')
    activity_type = models.ForeignKey(
        'ActivityType',
        on_delete=models.PROTECT,
        null=False,
        help_text='Select the intended activity to be performed by the server')

    class Meta:
        """Metadata for the model."""
        ordering = ['client', 'server']
        verbose_name = 'Server history'
        verbose_name_plural = 'Server history'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('shepherd:history_update', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.server.ip_address} ({self.server.name}) [{self.activity_type.activity}]'

    @property
    def will_be_released(self):
        """Property to test if the provided end date within 24-48 hours."""
        if (
            date.today() == self.end_date or
            date.today() == datetime.timedelta(days=1) or
            date.today() > self.end_date
        ):
            return True
        return False


class TransientServer(models.Model):
    """Model for recording the use of short-lived cloud servers.

    There are foreign keys for the `ServerRole`,`ActivityType`, `Client`,
    `Project`, `ServerProvider`, and `User` models.
    """
    ip_address = models.GenericIPAddressField(
        'IP Address',
        max_length=100,
        unique=True,
        help_text='Enter the server IP address')
    name = models.CharField(
        'Name',
        max_length=100,
        null=True,
        blank=True,
        help_text='Enter the server\'s name (typically hostname)')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='use this area to provide project-related notes, such as '
                  'how the server will be used/how it worked out')
    # Foreign Keys
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE,
        null=True,
        help_text='Select the project associated with this server')
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Select the user who added this server')
    server_provider = models.ForeignKey(
        'ServerProvider',
        on_delete=models.PROTECT,
        null=True,
        help_text='Select the service provider for this server')
    server_role = models.ForeignKey(
        'ServerRole',
        on_delete=models.PROTECT,
        null=False,
        blank=True,
        help_text='Select the role this VPS will play')
    activity_type = models.ForeignKey(
        'ActivityType',
        on_delete=models.PROTECT,
        null=False,
        blank=True,
        help_text='Select how this VPS will be used')

    class Meta:
        """Metadata for the model."""
        ordering = ['project', 'server_provider', 'ip_address', 'server_role', 'name']
        verbose_name = 'Virtual private server'
        verbose_name_plural = 'Virtual private servers'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.ip_address} ({self.name}) [{self.server_provider}]'


class DomainServerConnection(models.Model):
    """Model for recording which domains are used with with servers for a project.

    There are foreign keys for the `Domain`, `Server`, `TransientServer`, and
    `Project` models.
    """
    endpoint = models.CharField(
        'CDN Endpoint',
        max_length=100,
        null=True,
        blank=True,
        help_text='The CDN endpoint used with this link, if any')
    subdomain = models.CharField(
        'Subdomain',
        max_length=100,
        blank=True,
        null=True,
        default='*',
        help_text='The subdomain used for this domain record')
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE)
    domain = models.ForeignKey(
        'History',
        on_delete=models.CASCADE,
        help_text='Select the domain to link to one of the servers '
                  'provisioned for this project')
    static_server = models.ForeignKey(
        'ServerHistory',
        on_delete=models.CASCADE,
        null=True, blank=True)
    transient_server = models.ForeignKey(
        'TransientServer',
        on_delete=models.CASCADE,
        null=True,
        blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['project', 'domain']
        verbose_name = 'Domain and server record'
        verbose_name_plural = 'Domain and server records'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        # Only one server will be set so this adds nothing to something
        server = f'{self.static_server}{self.transient_server}'
        return f'{self.subdomain}.{self.domain} used with {server}'


class DomainNote(models.Model):
    """Model representing notes for domains.

    There are foreign keys for the `Domain` and `User` models.
    """
    # This field is automatically filled with the current date
    timestamp = models.DateField(
        'Timestamp',
        auto_now_add=True,
        max_length=100,
        help_text='Creation timestamp')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to add a note to this domain - it can be '
                  'anything you want others to see/know about the domain')
    # Foreign Keys
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['domain', '-timestamp']
        verbose_name = 'Domain note'
        verbose_name_plural = 'Domain notes'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.domain} {self.timestamp}: {self.note}'


class ServerNote(models.Model):
    """Model representing notes for servers.

    There are foreign keys for the `Server` and `User` models.
    """
    # This field is automatically filled with the current date
    timestamp = models.DateField(
        'Timestamp',
        auto_now_add=True,
        max_length=100,
        help_text='Creation timestamp')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to add a note to this server - it can be '
                  'anything you want others to see/know about the server')
    # Foreign Keys
    server = models.ForeignKey(
        'StaticServer', on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['server', '-timestamp']
        verbose_name = 'Server note'
        verbose_name_plural = 'Server notes'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.server} {self.timestamp}: {self.note}'


class AuxServerAddress(models.Model):
    """Model representing auxiliary IP addresses for servers.

    There are foreign keys for the `StaticServer` model.
    """
    ip_address = models.GenericIPAddressField(
        'IP Address',
        max_length=100,
        unique=True,
        help_text='Enter the auxiliary IP address for the server')
    primary = models.BooleanField(
        'Primary Address',
        default=False,
        help_text='Mark the address as the server\'s primary address')
    # Foreign Keys
    static_server = models.ForeignKey(
        StaticServer,
        on_delete=models.CASCADE,
        null=False)

    class Meta:
        """Metadata for the model."""
        ordering = ['static_server', 'ip_address']
        verbose_name = 'Auxiliary IP address'
        verbose_name_plural = 'Auxiliary IP addresses'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.ip_address}'
