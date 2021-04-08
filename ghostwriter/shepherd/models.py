"""This contains all of the database models for the Shepherd application."""

# Standard Libraries
import datetime
import json
from datetime import date

# Django Imports
from django.conf import settings
from django.db import models
from django.urls import reverse


class HealthStatus(models.Model):
    """
    Stores an individual health status.
    """

    health_status = models.CharField(
        max_length=255,
        unique=True,
        help_text="Health status type (e.g. Healthy, Burned)",
    )

    def count_status(self):
        """
        Count and return the number of :model:`shepherd.Domain` associated with
        an instance.
        """
        return Domain.objects.filter(health_status=self).count()

    count = property(count_status)

    class Meta:
        ordering = ["health_status"]
        verbose_name = "Health status"
        verbose_name_plural = "Health status"

    def __str__(self):
        return self.health_status


class DomainStatus(models.Model):
    """
    Stores an individual domain status.
    """

    domain_status = models.CharField(
        max_length=255, unique=True, help_text="Domain status type (e.g. Available)"
    )

    def count_status(self):
        """
        Count and return the number of :model:`shepherd.Domain` associated with
        an instance.
        """
        return Domain.objects.filter(domain_status=self).count()

    count = property(count_status)

    class Meta:
        ordering = ["domain_status"]
        verbose_name = "Domain status"
        verbose_name_plural = "Domain status"

    def __str__(self):
        return self.domain_status


class WhoisStatus(models.Model):
    """
    Stores an individual Whois status.
    """

    whois_status = models.CharField(
        max_length=255,
        unique=True,
        help_text="WHOIS privacy status (e.g. Enabled, Disabled)",
    )

    def count_status(self):
        """
        Count and return the number of :model:`shepherd.Domain` associated with
        an instance.
        """
        return Domain.objects.filter(whois_status=self).count()

    count = property(whois_status)

    class Meta:
        ordering = ["whois_status"]
        verbose_name = "WHOIS status"
        verbose_name_plural = "WHOIS status"

    def __str__(self):
        return self.whois_status


class ActivityType(models.Model):
    """
    Stores an individual acttivity type.
    """

    activity = models.CharField(
        max_length=255,
        unique=True,
        help_text="Reason for the use of the asset (e.g. C2, Phishing)",
    )

    class Meta:
        ordering = ["activity"]
        verbose_name = "Activity type"
        verbose_name_plural = "Activity types"

    def __str__(self):
        return self.activity


class DomainManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Domain(models.Model):
    """
    Stores an individual domain, related to :model:`shepherd.WhoisStatus`,
    :model:`shepherd.HealthStatus`, :model:`shepherd.DomainStatus`,
    and :model:`users.User`.
    """

    name = models.CharField(
        "Name", max_length=255, unique=True, help_text="Enter the domain name"
    )
    registrar = models.CharField(
        "Registrar",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the name of the registrar where this domain is registered",
    )
    dns_record = models.TextField(
        "DNS Records",
        null=True,
        blank=True,
        help_text="Enter the domain's DNS records - leave blank if you will run DNS updates later",
    )
    health_dns = models.CharField(
        "DNS Health",
        max_length=255,
        null=True,
        blank=True,
        help_text='Enter passive DNS information from VirusTotal - leave blank or enter "Healthy" if you do not know',
    )
    creation = models.DateField(
        "Purchase Date", help_text="Select the date the domain was purchased"
    )
    expiration = models.DateField(
        "Expiration Date", help_text="Select the date the domain will expire"
    )
    last_health_check = models.DateField(
        "Last Health Check",
        help_text="The date and time of the latest health check for this domain name",
        blank=True,
        null=True,
    )
    vt_permalink = models.CharField(
        "VirusTotal Permalink",
        max_length=255,
        null=True,
        blank=True,
        help_text="VirusTotal's permalink for scan results of this domain",
    )
    all_cat = models.TextField(
        "All Categories",
        null=True,
        blank=True,
        help_text="Enter all categories applied to this domain",
    )
    ibm_xforce_cat = models.CharField(
        "IBM X-Force",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the list of categories determined by IBM X-Force",
    )
    talos_cat = models.CharField(
        "Cisco Talos",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the list of categories determined by Cisco Talos",
    )
    bluecoat_cat = models.CharField(
        "Bluecoat",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the list of categories determined by Bluecoat",
    )
    fortiguard_cat = models.CharField(
        "Fortiguard",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the list of categories determined by Fortiguard",
    )
    opendns_cat = models.CharField(
        "OpenDNS",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the list of categories determined by OpenDNS",
    )
    trendmicro_cat = models.CharField(
        "TrendMicro",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the list of categories determined by TrendMicro",
    )
    mx_toolbox_status = models.CharField(
        "MX Toolbox Status",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the domain spam/blacklist status as determined by MX Toolbox",
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to provide notes and thoughts behind its purchase and intended use",
    )
    burned_explanation = models.TextField(
        "Health Explanation",
        null=True,
        blank=True,
        help_text="Provide details such as how the domain was detected, why it was blacklisted for spam, if it was flagged with a bad category, etc.",
    )
    auto_renew = models.BooleanField(
        "Auto Renew",
        default=True,
        help_text="Whether or not the domain is set to renew automatically with the registrar",
    )
    expired = models.BooleanField(
        "Expiration Status",
        default=False,
        help_text="Whether or not the domain registration has expired",
    )
    # Foreign Keys
    whois_status = models.ForeignKey(
        "WhoisStatus",
        on_delete=models.PROTECT,
        null=True,
        default=1,
        help_text="The domain's WHOIS privacy status - you want this to be Enabled with your registrar",
    )
    health_status = models.ForeignKey(
        "HealthStatus",
        on_delete=models.PROTECT,
        null=True,
        default=1,
        help_text="The domain's current health status - set to Healthy if you are not sure and assumed the domain is ready to be used",
    )
    domain_status = models.ForeignKey(
        "DomainStatus",
        on_delete=models.PROTECT,
        null=True,
        default=1,
        help_text="The domain's current status - set to Available in most cases, or set to Reserved if it should not be used yet",
    )
    last_used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The last user to checkout this domain",
    )

    objects = DomainManager()

    class Meta:
        ordering = ["health_status", "name", "expiration"]
        verbose_name = "Domain"
        verbose_name_plural = "Domains"

    def natural_key(self):
        return (self.name,)

    def get_absolute_url(self):
        return reverse("shepherd:domain_detail", args=[str(self.id)])

    def clean(self, *args, **kwargs):
        self.name = self.name.lower().replace(" ", "")
        super(Domain, self).clean(*args, **kwargs)

    def get_domain_age(self):
        """
        Calculate the domain's age based on the current date and the instance's creation DateField.
        """
        if self.is_expired():
            time_delta = self.expiration - self.creation
        else:
            time_delta = date.today() - self.creation
        return "{} days".format(time_delta.days)

    def is_expired(self):
        """
        Check if the domain's expiration DateField value is in the past.
        """
        expired = False
        if date.today() > self.expiration:
            if not self.auto_renew:
                expired = True
        return expired

    def is_expiring_soon(self):
        """
        Check if the domain's expiration DateField value is in the near future.
        """
        expiring_soon = False
        delta = date.today() + datetime.timedelta(days=30)
        if self.expiration <= delta:
            if not self.auto_renew:
                expiring_soon = True
        return expiring_soon

    def get_list(self):
        """
        Return an instance's dns_record field value as a list.
        """
        if self.dns_record:
            try:
                json_acceptable_string = self.dns_record.replace('"', "").replace(
                    "'", '"'
                )
                if json_acceptable_string:
                    return json.loads(json_acceptable_string)
                else:
                    return None
            except Exception:
                return self.dns_record
        else:
            return None

    def __str__(self):
        return f"{self.name} ({self.health_status})"


class History(models.Model):
    """
    Stores an individual domain checkout, related to :model:`rolodex.Client`,
    :model:`users.User`, :model:`rolodex.Project`, :model:`shepherd.ActivityType`,
    and :model:`shepherd.Domain`.
    """

    start_date = models.DateField(
        "Start Date", help_text="Select the start date of the project"
    )
    end_date = models.DateField(
        "End Date", help_text="Select the end date of the project"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to provide project-related notes, such as how the domain will be used/how it worked out",
    )
    # Foreign Keys
    domain = models.ForeignKey(
        "Domain",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the domain you wish to check-out",
    )
    client = models.ForeignKey(
        "rolodex.Client",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the client associated with this checkout",
    )
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project associated with the checkout - this field will populate after you select a client above",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select the user checking out this domain",
    )
    activity_type = models.ForeignKey(
        "ActivityType",
        on_delete=models.PROTECT,
        null=False,
        help_text="Select the intended use of this domain",
    )

    class Meta:
        ordering = ["client", "domain", "activity_type", "start_date"]
        verbose_name = "Domain history"
        verbose_name_plural = "Domain history"

    def get_absolute_url(self):
        return reverse("shepherd:history_update", args=[str(self.id)])

    def __str__(self):
        return f"{self.project} : {self.domain.name}"

    @property
    def will_be_released(self):
        """
        Test if the instance's end_date DateField value is within the next 24-48 hours.
        """
        if (
            date.today() == self.end_date
            or date.today() == datetime.timedelta(days=1)
            or date.today() > self.end_date
        ):
            return True
        return False


class ServerStatus(models.Model):
    """
    Stores an individual server status.
    """

    server_status = models.CharField(
        max_length=255, unique=True, help_text="Server status (e.g. Available)"
    )

    def count_status(self):
        """
        Count and return the number of :model:`shepherd.StaticServer` associated with
        an instance.
        """
        return StaticServer.objects.filter(server_status=self).count()

    count = property(count_status)

    class Meta:

        ordering = ["server_status"]
        verbose_name = "Server status"
        verbose_name_plural = "Server status"

    def __str__(self):
        return self.server_status


class ServerProvider(models.Model):
    """
    Stores an individual server provider.
    """

    server_provider = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the server provider (e.g. Amazon Web Services, Azure)",
    )

    def count_provider(self):
        """
        Count and return the number of :model:`shepherd.StaticServer` associated with
        an instance.
        """
        return StaticServer.objects.filter(server_provider=self).count()

    count = property(count_provider)

    class Meta:
        ordering = ["server_provider"]
        verbose_name = "Server provider"
        verbose_name_plural = "Server providers"

    def __str__(self):
        return self.server_provider


class StaticServer(models.Model):
    """
    Stores an individual static server, related to :model:`users.User`,
    :model:`shepherd.ServerProvider`, and :model:`shepherd.ServerStatus`.
    """

    ip_address = models.GenericIPAddressField(
        "IP Address",
        max_length=255,
        unique=True,
        help_text="Enter the server's static IP address",
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to provide server-related notes, such as its designated use or how it can be used",
    )
    name = models.CharField(
        "Name",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the server's name (typically hostname)",
    )
    # Foreign Keys
    server_status = models.ForeignKey(
        ServerStatus,
        on_delete=models.PROTECT,
        null=True,
        help_text="Enter the server's current status - typically Available unless it needs to be set aside immediately upon creation",
    )
    server_provider = models.ForeignKey(
        ServerProvider,
        on_delete=models.PROTECT,
        null=True,
        help_text="Select the service provider for this server",
    )
    last_used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["server_status", "server_provider", "ip_address"]
        verbose_name = "Static server"
        verbose_name_plural = "Static servers"

    def get_absolute_url(self):
        return reverse("shepherd:server_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.ip_address} ({self.name}) [{self.server_provider}]"


class ServerRole(models.Model):
    """
    Stores an individual server role.
    """

    server_role = models.CharField(
        max_length=255,
        unique=True,
        help_text="A role for applied to the use of a server (e.g. Payload Delivery, Redirector)",
    )

    class Meta:
        ordering = ["server_role"]
        verbose_name = "Server role"
        verbose_name_plural = "Server roles"

    def __str__(self):
        return self.server_role


class ServerHistory(models.Model):
    """
    Stores an individual server checkout, related to :model:`rolodex.Project`,
    :model:`shepherd.ActivityType`, :model:`shepherd.StaticServer`,
    :model:`rolodex.Client`, :model:`users.User`, and :model:`shepherd.ServerRole`.
    """

    start_date = models.DateField(
        "Start Date", help_text="Select the start date of the project"
    )
    end_date = models.DateField(
        "End Date", help_text="Select the end date of the project"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to provide project-related notes, such as how the server/IP will be used",
    )
    # Foreign Keys
    server = models.ForeignKey(
        "StaticServer",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the server being checked out",
    )
    client = models.ForeignKey(
        "rolodex.Client",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the client associated with the checkout",
    )
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project associated with the checkout - this field will populate after you select a client above",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select the user associated with this checkout",
    )
    server_role = models.ForeignKey(
        "ServerRole",
        on_delete=models.PROTECT,
        null=False,
        help_text="Select the intended role the server will play",
    )
    activity_type = models.ForeignKey(
        "ActivityType",
        on_delete=models.PROTECT,
        null=False,
        help_text="Select the intended activity to be performed by the server",
    )

    class Meta:
        ordering = ["client", "server"]
        verbose_name = "Server history"
        verbose_name_plural = "Server history"

    def get_absolute_url(self):
        return reverse("shepherd:history_update", args=[str(self.id)])

    def __str__(self):
        return f"{self.server.ip_address} ({self.server.name}) [{self.activity_type.activity}]"

    def ip_address(self):
        """
        Return the ``ip_address`` field's value for the instance.
        """
        return self.server.ip_address

    def server_name(self):
        """
        Return the ``name`` field's value for the instance.
        """
        return self.server.name

    @property
    def will_be_released(self):
        """
        Test if the instance's ``end_date`` DateField value is within the next 24-48 hours.
        """
        if (
            date.today() == self.end_date
            or date.today() == datetime.timedelta(days=1)
            or date.today() > self.end_date
        ):
            return True
        return False


class TransientServer(models.Model):
    """
    Stores an individual temporary virtual private server, related to
    :model:`rolodex.Project`, :model:`shepherd.ActivityType`,
    :model:`shepherd.ServerProvider`, :model:`rolodex.Client`, :model:`users.User`, and
    :model:`shepherd.ServerRole`.
    """

    ip_address = models.GenericIPAddressField(
        "IP Address",
        max_length=255,
        unique=True,
        help_text="Enter the server IP address",
    )
    name = models.CharField(
        "Name",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the server's name (typically hostname)",
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="use this area to provide project-related notes, such as how the server will be used/how it worked out",
    )
    # Foreign Keys
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project associated with this server",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select the user who added this server",
    )
    server_provider = models.ForeignKey(
        "ServerProvider",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select the service provider for this server",
    )
    server_role = models.ForeignKey(
        "ServerRole",
        on_delete=models.PROTECT,
        null=False,
        blank=True,
        help_text="Select the role this VPS will play",
    )
    activity_type = models.ForeignKey(
        "ActivityType",
        on_delete=models.PROTECT,
        null=False,
        blank=True,
        help_text="Select how this VPS will be used",
    )

    class Meta:
        ordering = ["project", "server_provider", "ip_address", "server_role", "name"]
        verbose_name = "Virtual private server"
        verbose_name_plural = "Virtual private servers"

    def __str__(self):
        return f"{self.ip_address} ({self.name}) [{self.server_provider}]"


class DomainServerConnection(models.Model):
    """
    Stores an individual link between one :model:`shepherd.Domain` and one
    :model:`shepherd.StaticServer` or :model:`shepherd.TransientServer`.

    Each link is associated with an one :model:`rolodex.Project`.
    """

    endpoint = models.CharField(
        "CDN Endpoint",
        max_length=255,
        null=True,
        blank=True,
        help_text="The CDN endpoint used with this link, if any",
    )
    subdomain = models.CharField(
        "Subdomain",
        max_length=255,
        blank=True,
        null=True,
        default="*",
        help_text="The subdomain used for this domain record",
    )
    project = models.ForeignKey("rolodex.Project", on_delete=models.CASCADE)
    domain = models.ForeignKey(
        "History",
        on_delete=models.CASCADE,
        help_text="Select the domain to link to one of the servers provisioned for this project",
    )
    static_server = models.ForeignKey(
        "ServerHistory", on_delete=models.CASCADE, null=True, blank=True
    )
    transient_server = models.ForeignKey(
        "TransientServer", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:

        ordering = ["project", "domain"]
        verbose_name = "Domain and server record"
        verbose_name_plural = "Domain and server records"

    def domain_name(self):
        """
        Return the ``name`` field's value for the instance.
        """
        return self.domain.domain.name

    def __str__(self):
        # Only one server will be set so this adds nothing to something
        server = f"{self.static_server}{self.transient_server}"
        return f"{self.subdomain}.{self.domain} used with {server}"


class DomainNote(models.Model):
    """
    Stores an individual domain note, related to :model:`shepherd.Domain` and :model:`users.User`.
    """

    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to add a note to this domain",
    )
    # Foreign Keys
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["domain", "-timestamp"]
        verbose_name = "Domain note"
        verbose_name_plural = "Domain notes"

    def __str__(self):
        return f"{self.domain} {self.timestamp}: {self.note}"


class ServerNote(models.Model):
    """
    Stores an individual server note, related to :model:`shepherd.StaticServer` and :model:`users.User`.
    """

    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to add a note to this server",
    )
    # Foreign Keys
    server = models.ForeignKey("StaticServer", on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["server", "-timestamp"]
        verbose_name = "Server note"
        verbose_name_plural = "Server notes"

    def __str__(self):
        return f"{self.server} {self.timestamp}: {self.note}"


class AuxServerAddress(models.Model):
    """
    Stores an individual auxiliary IP address, related to :model:`shepherd.StaticServer`.
    """

    ip_address = models.GenericIPAddressField(
        "IP Address",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the auxiliary IP address for the server",
    )
    primary = models.BooleanField(
        "Primary Address",
        default=False,
        help_text="Mark the address as the server's primary address",
    )
    # Foreign Keys
    static_server = models.ForeignKey(StaticServer, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["static_server", "ip_address"]
        verbose_name = "Auxiliary IP address"
        verbose_name_plural = "Auxiliary IP addresses"

    def __str__(self):
        return f"{self.ip_address}"
