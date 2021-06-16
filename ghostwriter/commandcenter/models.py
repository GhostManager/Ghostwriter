"""This contains all of the database models for the CommandCenter application."""

# Django Imports
from django.db import models

# Ghostwriter Libraries
from ghostwriter.singleton.models import SingletonModel


def sanitize(sensitive_thing):
    """
    Sanitize the provided input and return for display in a template.
    """
    sanitized_string = sensitive_thing
    length = len(sensitive_thing)
    if sensitive_thing:
        if "http" in sensitive_thing:
            # Split the URL – expecting a Slack (or other) webhook
            sensitive_thing = sensitive_thing.split("/")
            # Get just the last part for sanitization
            webhook_tail = "".join(sensitive_thing[-1:])
            length = len(webhook_tail)
            # Construct a sanitized string
            sanitized_string = (
                "/".join(sensitive_thing[:-1])
                + "/"
                + webhook_tail[0:4]
                + "\u2717" * (length - 8)
                + webhook_tail[length - 5 : length - 1]
            )
        # Handle anything else that's long enough to be a key
        elif length > 15:
            sanitized_string = (
                sensitive_thing[0:4]
                + "\u2717" * (length - 8)
                + sensitive_thing[length - 5 : length - 1]
            )
    return sanitized_string


class NamecheapConfiguration(SingletonModel):
    enable = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, default="Namecheap API Key")
    username = models.CharField(max_length=255, default="Account Username")
    api_username = models.CharField(max_length=255, default="API Username")
    client_ip = models.CharField(max_length=255, default="Whitelisted IP Address")
    page_size = models.IntegerField(default=100)

    def __str__(self):
        return "Namecheap Configuration"

    class Meta:
        verbose_name = "Namecheap Configuration"

    @property
    def sanitized_api_key(self):
        return sanitize(self.api_key)


class ReportConfiguration(SingletonModel):
    enable_borders = models.BooleanField(
        default=False, help_text="Enable borders around images in Word documents"
    )
    border_weight = models.IntegerField(
        default=12700,
        help_text="Weight in EMUs – 12700 is equal to the 1pt weight in Word",
    )
    border_color = models.CharField(
        "Picture Border Color", max_length=6, default="2D2B6B"
    )

    prefix_figure = models.CharField(
        "Character Before Figure Captions",
        max_length=255,
        default=u"\u2013",
        help_text="Unicode character to place between the label and your figure caption in Word reports",
    )
    label_figure = models.CharField(
        "Label Used for Figures",
        max_length=255,
        default="Figure",
        help_text="The label that comes before the figure number and caption in Word reports",
    )
    prefix_table = models.CharField(
        "Character Before Table Titles",
        max_length=255,
        default=u"\u2013",
        help_text="Unicode character to place between the label and your table caption in Word reports",
    )
    label_table = models.CharField(
        "Label Used for Tables",
        max_length=255,
        default="Table",
        help_text="The label that comes before the table number and caption in Word reports",
    )
    # Foreign Keys
    default_docx_template = models.ForeignKey(
        "reporting.reporttemplate",
        related_name="reportconfiguration_docx_set",
        on_delete=models.SET_NULL,
        limit_choices_to={
            "doc_type__doc_type__iexact": "docx",
        },
        null=True,
        blank=True,
        help_text="Select a default Word template",
    )
    default_pptx_template = models.ForeignKey(
        "reporting.reporttemplate",
        related_name="reportconfiguration_pptx_set",
        on_delete=models.SET_NULL,
        limit_choices_to={
            "doc_type__doc_type__iexact": "pptx",
        },
        null=True,
        blank=True,
        help_text="Select a default PowerPoint template",
    )

    def __str__(self):
        return "Global Report Configuration"

    class Meta:
        verbose_name = "Global Report Configuration"

    @property
    def border_color_rgb(self):
        """
        Return the border color code as a list of RGB values.
        """
        return tuple(int(self.color[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def border_color_hex(self):
        """
        Return the border color code as a list of hexadecimal.
        """
        n = 2
        return tuple(
            hex(int(self.color[i : i + n], 16)) for i in range(0, len(self.color), n)
        )


class SlackConfiguration(SingletonModel):
    enable = models.BooleanField(default=False)
    webhook_url = models.CharField(
        max_length=255, default="https://hooks.slack.com/services/<your_webhook_url>"
    )
    slack_emoji = models.CharField(
        max_length=255,
        default=":ghost:",
        help_text="Emoji used for the avatar wrapped in colons",
    )
    slack_channel = models.CharField(
        max_length=255,
        default="#ghostwriter",
        help_text="Default channel for Slack notifications",
    )
    slack_username = models.CharField(
        max_length=255,
        default="Ghostwriter",
        help_text="Display name for the Slack bot",
    )
    slack_alert_target = models.CharField(
        max_length=255,
        default="<!here>",
        help_text="Alert target for the notifications – blank for no target",
    )

    def __str__(self):
        return "Slack Configuration"

    class Meta:
        verbose_name = "Slack Configuration"

    @property
    def sanitized_webhook(self):
        return sanitize(self.webhook_url)


class CompanyInformation(SingletonModel):
    company_name = models.CharField(
        max_length=255,
        default="SpecterOps",
        help_text="Company name handle to reference in reports",
    )
    company_twitter = models.CharField(
        "Twitter Handle",
        max_length=255,
        default="@specterops",
        help_text="Twitter handle to reference in reports",
    )
    company_email = models.CharField(
        max_length=255,
        default="info@specterops.io",
        help_text="Email address to reference in reports",
    )

    def __str__(self):
        return "Company Information"

    class Meta:
        verbose_name = "Company Information"


class CloudServicesConfiguration(SingletonModel):
    enable = models.BooleanField(
        default=False, help_text="Enable to allow the cloud monitoring task to run"
    )
    aws_key = models.CharField(
        "AWS Access Key", max_length=255, default="Your AWS Access Key"
    )
    aws_secret = models.CharField(
        "AWS Secret Key", max_length=255, default="Your AWS Secret Key"
    )
    do_api_key = models.CharField(
        "Digital Ocean API Key", max_length=255, default="Digital Ocean API Key"
    )
    ignore_tag = models.CharField(
        "Ignore Tags",
        max_length=255,
        default="gw_ignore",
        help_text="Ghostwriter will ignore cloud assets with one of these tags (comma-separated list)",
    )

    def __str__(self):
        return "Cloud Services Configuration"

    class Meta:
        verbose_name = "Cloud Services Configuration"

    @property
    def sanitized_aws_key(self):
        return sanitize(self.aws_key)

    @property
    def sanitized_aws_secret(self):
        return sanitize(self.aws_secret)

    @property
    def sanitized_do_api_key(self):
        return sanitize(self.do_api_key)


class VirusTotalConfiguration(SingletonModel):
    enable = models.BooleanField(
        default=False, help_text="Enable to allow domain health checks with VirusTotal"
    )
    api_key = models.CharField(max_length=255, default="VirusTotal API Key")
    sleep_time = models.IntegerField(
        default=20,
        help_text="Sleep time in seconds – free API keys can only make 4 requests per minute",
    )

    def __str__(self):
        return "VirusTotal Configuration"

    class Meta:
        verbose_name = "VirusTotal Configuration"

    @property
    def sanitized_api_key(self):
        return sanitize(self.api_key)
