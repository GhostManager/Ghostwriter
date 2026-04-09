"""This contains all the database models for the CommandCenter application."""

import json
from dataclasses import dataclass
from typing import Any, Callable, NamedTuple
from urllib.parse import urlparse

# Django Imports
from django.db import models
from django.db.models import F, Max, Q
from django.db.transaction import atomic
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from ghostwriter.modules.reportwriter.forms import JinjaRichTextField
from timezone_field import TimeZoneField

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
            sanitized_string = sensitive_thing[0:4] + "\u2717" * (length - 8) + sensitive_thing[length - 5 : length - 1]
    return sanitized_string

def validate_endpoint(value: str):
    url = urlparse(value)
    if not url.scheme:
        raise ValidationError(_("Missing scheme on URL"))
    if not url.hostname:
        raise ValidationError(_("Missing hostname on URL"))
    if url.path:
        raise ValidationError(_("Paths on endpoint URL are not supported"))

class BloodHoundConfiguration(SingletonModel):
    """
    BloodHoundConfiguration represents a global BloodHound API integration that can be used to
    access the BloodHound API of the configured instance.
    """
    bloodhound_api_root_url = models.CharField(
        max_length=255,
        verbose_name="BloodHound API URL",
        help_text="The URL of the BloodHound instance",
        default="",
        blank=True,
        validators=[validate_endpoint],
    )

    bloodhound_api_key_id = models.CharField(
        max_length=255,
        verbose_name="BloodHound API Key ID",
        help_text="The ID portion of a BloodHound API Key",
        default="",
        blank=True,
    )

    bloodhound_api_key_token = models.CharField(
        max_length=255,
        verbose_name="BloodHound API Key Token",
        help_text="The token portion of a BloodHound API Key",
        default="",
        blank=True,
    )

    bloodhound_results = models.JSONField(
        null=True,
        verbose_name="Bloodhound Data",
        editable=False,
    )

    def has_bloodhound_api(self) -> bool:
        return self.bloodhound_api_root_url != "" and self.bloodhound_api_key_id != "" and self.bloodhound_api_key_token != ""

    def __str__(self):
        return "BloodHound API Configuration"

    class Meta:
        verbose_name = "BloodHound API Configuration"
        # constraints = [
        #     models.CheckConstraint(
        #         check=models.Q(
        #             api_root_url="",
        #             api_key_id="",
        #             api_key_token=""
        #         ) | models.Q(
        #             ~models.Q(api_root_url="") &
        #             ~models.Q(api_key_id="") &
        #             ~models.Q(api_key_token="")
        #         ),
        #         name="commandcenter_bloodhoundconfiguration_all_or_none_set",
        #         #violation_error_message="Incomplete BloodHound API Configuration",
        #     ),
        # ]


class NamecheapConfiguration(SingletonModel):
    enable = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, default="Namecheap API Key", help_text="Your Namecheap API key")
    username = models.CharField(max_length=255, default="Account Username", help_text="Your Namecheap username")
    api_username = models.CharField(
        "API Username",
        max_length=255,
        default="API Username",
        help_text="Your Namecheap API username",
    )
    client_ip = models.CharField(
        "Whitelisted IP Address",
        max_length=255,
        default="Whitelisted IP Address",
        help_text="Your external IP address registered with Namecheap",
    )
    page_size = models.IntegerField(
        "Page Size",
        default=100,
        help_text="Maximum number of domains to return (100 is the max allowed)",
    )

    def __str__(self):
        return "Namecheap Configuration"

    class Meta:
        verbose_name = "Namecheap Configuration"

    @property
    def sanitized_api_key(self):
        return sanitize(self.api_key)


class ReportConfiguration(SingletonModel):
    @dataclass(frozen=True)
    class OutlineTagRules:
        """Normalized tag rules for narrative outline generation."""

        exact_tags: tuple[str, ...]
        prefix_tags: tuple[str, ...]

    OUTLINE_DEFAULT_TAGS = ("report", "evidence")

    enable_borders = models.BooleanField(default=False, help_text="Enable borders around images in Word documents")
    border_weight = models.IntegerField(
        default=12700,
        help_text="Weight in EMUs – 12700 is equal to the 1pt weight in Word",
    )
    border_color = models.CharField("Picture Border Color", max_length=6, default="2D2B6B")

    prefix_figure = models.CharField(
        "Character Before Figure Captions",
        max_length=255,
        default=" \u2013 ",
        help_text="Unicode characters to place between the label and your figure caption in Word reports (include any desired spaces before and after)",
    )
    label_figure = models.CharField(
        "Label Used for Figures",
        max_length=255,
        default="Figure",
        help_text="The label that comes before the figure number and caption in Word reports",
    )
    figure_caption_location = models.CharField(
        "Figure Caption Location",
        max_length=10,
        choices=[("top", "Top"), ("bottom", "Bottom")],
        default="bottom",
        help_text="Where to place figure captions relative to the figure",
    )
    prefix_table = models.CharField(
        "Character Before Table Titles",
        max_length=255,
        default=" \u2013 ",
        help_text="Unicode characters to place between the label and your table caption in Word reports (include any desired spaces before and after)",
    )
    label_table = models.CharField(
        "Label Used for Tables",
        max_length=255,
        default="Table",
        help_text="The label that comes before the table number and caption in Word reports",
    )
    table_caption_location = models.CharField(
        "Table Caption Location",
        max_length=10,
        choices=[("top", "Top"), ("bottom", "Bottom")],
        default="top",
        help_text="Where to place table captions relative to the table",
    )
    report_filename = models.CharField(
        "Default Name for Report Downloads",
        max_length=255,
        default='{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report',
        help_text="Jinja2 template for report filenames. All template variables are available, plus {{now}} and {{company_name}}. The file extension is added to this. Individual templates may override this option.",
    )
    project_filename = models.CharField(
        "Default Name for Project Downloads",
        max_length=255,
        default='{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report',
        help_text="Jinja2 template for project filenames. All template variables are available, plus {{now}} and {{company_name}}. The file extension is added to this. Individual templates may override this option.",
    )
    title_case_captions = models.BooleanField(
        "Title Case Captions",
        default=True,
        help_text="Capitalize the first letter of each word in figure and table captions",
    )
    title_case_exceptions = models.CharField(
        "Title Case Exceptions",
        default="a,as,at,an,and,of,the,is,to,by,for,in,on,but,or",
        help_text="Comma-separated list of words to exclude from title case conversion",
        blank=True,
        max_length=255,
    )
    target_delivery_date = models.IntegerField(
        "Target Delivery Date",
        default=5,
        help_text="Number of business days from the project's end date to set as the default target delivery date",
    )
    default_cvss_version = models.CharField(
        "Default CVSS Calculator Version",
        max_length=10,
        choices=[("3.1", "CVSS v3.1"), ("4.0", "CVSS v4.0")],
        default="3.1",
        help_text="Default CVSS calculator version to display when no user preference is saved in browser local storage",
    )
    outline_tags = models.CharField(
        "Narrative Outline Tags",
        max_length=255,
        default="report,evidence",
        help_text=(
            "Comma-separated list of additional tags to include in generated narrative "
            "outlines. Built-in `report` and `evidence` tags are always included and "
            "cannot be removed here. Use exact tags like `credentials` or `detection`, wildcard "
            "prefixes like `cred*`, or namespaced prefixes like `att&ck:`. Matching is "
            "case-insensitive."
        ),
        blank=True,
    )
    # Foreign Keys
    default_docx_template = models.ForeignKey(
        "reporting.reporttemplate",
        related_name="reportconfiguration_docx_set",
        on_delete=models.SET_NULL,
        limit_choices_to={
            "doc_type__doc_type__iexact": "docx",
            "client__isnull": True,
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
            "client__isnull": True,
        },
        null=True,
        blank=True,
        help_text="Select a default PowerPoint template",
    )

    def __str__(self):
        return "Global Report Configuration"

    @classmethod
    def parse_outline_tags(
        cls,
        outline_tags: str | None,
        include_defaults: bool = True,
    ) -> "ReportConfiguration.OutlineTagRules":
        """
        Parse outline tag configuration into normalized exact and prefix match rules.

        Matching is case-insensitive, ignores empty comma-separated segments, and supports
        trailing ``*`` or ``:`` to indicate a prefix match. The built-in ``report`` and
        ``evidence`` tags are included by default for backwards-compatible behavior.
        """

        exact_tags: list[str] = []
        prefix_tags: list[str] = []
        seen_exact: set[str] = set()
        seen_prefix: set[str] = set()

        def add_exact(tag: str):
            if tag and tag not in seen_exact:
                seen_exact.add(tag)
                exact_tags.append(tag)

        def add_prefix(prefix: str):
            if prefix and prefix not in seen_prefix:
                seen_prefix.add(prefix)
                prefix_tags.append(prefix)

        if include_defaults:
            for tag in cls.OUTLINE_DEFAULT_TAGS:
                add_exact(tag)

        for raw_token in (outline_tags or "").split(","):
            token = raw_token.strip().lower()
            if not token:
                continue
            if token.endswith("*"):
                add_prefix(token[:-1])
            elif token.endswith(":"):
                add_prefix(token)
            else:
                add_exact(token)

        return cls.OutlineTagRules(tuple(exact_tags), tuple(prefix_tags))

    @classmethod
    def normalize_outline_tags(cls, outline_tags: str | None) -> str:
        """Return the canonical comma-separated storage form for outline tags."""

        rules = cls.parse_outline_tags(outline_tags, include_defaults=False)
        return ",".join([*rules.exact_tags, *(f"{prefix}*" for prefix in rules.prefix_tags)])

    @classmethod
    def validate_outline_tags(cls, outline_tags: str | None) -> str:
        """
        Validate and normalize outline tags for configuration storage.

        The input may contain exact tags or prefix rules that end in ``*`` or ``:``.
        Empty tokens are ignored, and malformed wildcard tokens raise ``ValidationError``.
        """

        normalized_tokens: list[str] = []
        seen_tokens: set[str] = set()

        for raw_token in (outline_tags or "").split(","):
            token = raw_token.strip().lower()
            if not token:
                continue
            if token == "*" or token == ":":
                raise ValidationError(_("Outline tag wildcard rules must include a prefix before '*' or ':'"))
            if token.count("*") > 1 or "*" in token[:-1]:
                raise ValidationError(_("Outline tag wildcard rules may only include '*' at the end"))
            if token.endswith("*"):
                normalized = f"{token[:-1]}*"
                if normalized == "*":
                    raise ValidationError(_("Outline tag wildcard rules must include a prefix before '*'"))
            elif token.endswith(":"):
                if "*" in token or token[:-1].endswith(":"):
                    raise ValidationError(_("Outline tag ':' prefixes must end with a single trailing ':'"))
                normalized = token
            else:
                normalized = token

            if normalized not in seen_tokens:
                seen_tokens.add(normalized)
                normalized_tokens.append(normalized)

        return cls.normalize_outline_tags(",".join(normalized_tokens))

    def clear_incorrect_template_defaults(self, template):
        altered = False
        if self.default_docx_template == template:
            if template.client is not None or template.doc_type.doc_type != "docx":
                self.default_docx_template = None
                altered = True
        if self.default_pptx_template == template:
            if template.client is not None or template.doc_type.doc_type != "pptx":
                self.default_pptx_template = None
                altered = True
        return altered

    class Meta:
        verbose_name = "Global Report Configuration"


class SlackConfiguration(SingletonModel):
    enable = models.BooleanField(default=False)
    webhook_url = models.CharField(max_length=255, default="https://hooks.slack.com/services/<your_webhook_url>")
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
        help_text="Alert target for the notifications (e.g., <!here>) – blank for no target",
        blank=True,
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
    company_short_name = models.CharField(
        max_length=255,
        default="SO",
        help_text="Abbreviated company name to reference in reports",
    )
    company_address = models.TextField(
        default="14 N Moore St, New York, NY 10013",
        help_text="Company address to reference in reports",
        blank=True,
    )
    company_twitter = models.CharField(
        "Twitter Handle",
        max_length=255,
        default="@specterops",
        help_text="Twitter handle to reference in reports",
        blank=True,
    )
    company_email = models.CharField(
        max_length=255,
        default="info@specterops.io",
        help_text="Email address to reference in reports",
        blank=True,
    )

    def __str__(self):
        return "Company Information"

    class Meta:
        verbose_name = "Company Information"


class CloudServicesConfiguration(SingletonModel):
    enable = models.BooleanField(default=False, help_text="Enable to allow the cloud monitoring task to run")
    aws_key = models.CharField("AWS Access Key", max_length=255, default="Your AWS Access Key")
    aws_secret = models.CharField("AWS Secret Key", max_length=255, default="Your AWS Secret Key")
    do_api_key = models.CharField("Digital Ocean API Key", max_length=255, default="Digital Ocean API Key")
    ignore_tag = models.CharField(
        "Ignore Tags",
        max_length=255,
        default="gw_ignore",
        help_text="Ghostwriter will ignore cloud assets with one of these tags (comma-separated list)",
    )
    notification_delay = models.IntegerField(
        "Notification Delay",
        default=7,
        help_text="Number of days to delay cloud monitoring notifications for teardown",
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
    enable = models.BooleanField(default=False, help_text="Enable to allow domain health checks with VirusTotal")
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


class GeneralConfiguration(SingletonModel):
    default_timezone = TimeZoneField(
        "Default Timezone",
        default="America/Los_Angeles",
        help_text="Select a default timezone for clients and projects",
        use_pytz=False,
    )
    hostname = models.CharField(
        max_length=255,
        default="ghostwriter.local",
        help_text="Hostname or IP address for Ghostwriter (used for links in notifications)",
    )

    def __str__(self):
        return "General Settings"

    class Meta:
        verbose_name = "General Settings"


class BannerConfiguration(SingletonModel):
    enable_banner = models.BooleanField(default=False, help_text="Enable the homepage banner to display for all users")
    banner_title = models.CharField(
        max_length=255,
        default="",
        help_text="Title to display in the banner",
        blank=True,
    )
    banner_message = models.CharField(
        max_length=255,
        default="",
        help_text="Message to display in the banner",
        blank=True,
    )
    banner_link = models.CharField(
        max_length=255,
        default="",
        help_text="URL to link the banner to (leave blank for no link)",
        blank=True,
    )
    public_banner = models.BooleanField(
        default=False,
        help_text="Display the banner to all users, including unauthenticated users on the login page",
    )
    expiry_date = models.DateTimeField("Display Until", help_text="Select the date when the banner should stop displaying (leave blank if it should not expire)", blank=True, null=True)

    def __str__(self):
        return "Banner Settings"

    class Meta:
        verbose_name = "Banner Configuration"


class IndentingJsonEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs["indent"] = "\t"
        super().__init__(*args, **kwargs)


class ExtraFieldType(NamedTuple):
    # Name displayed to the user
    display_name: str
    # Creates a form field to use for the field
    form_field: Callable[..., forms.Field]
    # Creates a form widget to use for the field
    form_widget: Callable[..., forms.widgets.Widget]
    # Parse a value from a string
    from_str: Callable[[str], Any]
    # Returns an "empty" value
    empty_value: Callable[[], Any]


def float_widget(*args, **kwargs):
    widget = forms.widgets.NumberInput(*args, **kwargs)
    widget.attrs.setdefault("step", "any")
    return widget


# Also edit frontend/src/extra_fields.tsx
EXTRA_FIELD_TYPES = {
    "checkbox": ExtraFieldType(
        display_name="Checkbox",
        form_field=lambda *args, **kwargs: forms.BooleanField(required=False, *args, **kwargs),
        form_widget=forms.widgets.CheckboxInput,
        from_str=bool,
        empty_value=lambda: False,
    ),
    "single_line_text": ExtraFieldType(
        display_name="Single-Line of Text",
        form_field=lambda *args, **kwargs: forms.CharField(required=False, *args, **kwargs),
        form_widget=forms.widgets.TextInput,
        from_str=lambda s: s,
        empty_value=lambda: "",
    ),
    "rich_text": ExtraFieldType(
        display_name="Formatted Text",
        form_field=lambda *args, **kwargs: JinjaRichTextField(required=False, *args, **kwargs),
        form_widget=forms.widgets.Textarea,
        from_str=lambda s: s,
        empty_value=lambda: "",
    ),
    "integer": ExtraFieldType(
        display_name="Integer",
        form_field=lambda *args, **kwargs: forms.IntegerField(required=False, *args, **kwargs),
        form_widget=forms.widgets.NumberInput,
        from_str=int,
        empty_value=lambda: 0,
    ),
    "float": ExtraFieldType(
        display_name="Number",
        form_field=lambda *args, **kwargs: forms.FloatField(required=False, *args, **kwargs),
        form_widget=float_widget,
        from_str=float,
        empty_value=lambda: 0.0,
    ),
    "json": ExtraFieldType(
        display_name="JSON",
        form_field=lambda *args, **kwargs: forms.JSONField(required=False, encoder=IndentingJsonEncoder, *args, **kwargs),
        form_widget=lambda: forms.widgets.Textarea(attrs={"class": "no-auto-tinymce"}),
        from_str=json.loads,
        empty_value=lambda: None,
    ),
}


class ExtraFieldModel(models.Model):
    model_internal_name = models.CharField(max_length=255, primary_key=True)
    model_display_name = models.CharField(max_length=255)
    is_collab_editable = models.BooleanField(default=False)

    def __str__(self):
        return "Extra fields for {}".format(self.model_display_name)

    class Meta:
        verbose_name = "Extra Field Configuration"


class ExtraFieldSpec(models.Model):
    target_model = models.ForeignKey(to=ExtraFieldModel, on_delete=models.CASCADE)
    internal_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(
        "Position",
        blank=True,
        null=True,
        help_text="Enter the display order for this extra field. Changing it will reorder the other extra fields for this model.",
        validators=[MinValueValidator(1)],
    )
    type = models.CharField(
        max_length=255, choices=[(key, typ.display_name) for (key, typ) in EXTRA_FIELD_TYPES.items()]
    )
    user_default_value = models.TextField(
        verbose_name="Value for New Objects",
        blank=True,
        default="",
    )

    @classmethod
    def for_model(cls, model):
        return cls.objects.filter(target_model=model._meta.label).order_by(F("position").asc(nulls_last=True), "id")

    @classmethod
    def for_instance(cls, instance):
        return cls.for_model(type(instance))

    @classmethod
    def initial_json(cls, model):
        return {v.internal_name: v.initial_value() for v in cls.for_model(model)}

    @classmethod
    def get_last_position(cls, target_model):
        target_model_id = cls._target_model_id(target_model)
        return cls.objects.filter(target_model=target_model_id).aggregate(max_position=Max("position"))["max_position"] or 0

    @staticmethod
    def _target_model_id(target_model):
        return getattr(target_model, "pk", target_model)

    @classmethod
    def _lock_target_model(cls, target_model_id):
        ExtraFieldModel.objects.select_for_update().get(pk=target_model_id)

    @classmethod
    def _shift_positions(cls, queryset, delta, target_model_id):
        queryset = queryset.order_by()
        if not queryset.exists():
            return

        target_ids = list(queryset.values_list("pk", flat=True))
        max_position = cls.get_last_position(target_model_id)
        offset = max_position + len(target_ids) + 1
        cls.objects.filter(pk__in=target_ids, target_model=target_model_id).update(position=F("position") + offset)
        cls.objects.filter(pk__in=target_ids, target_model=target_model_id).update(position=F("position") - offset + delta)

    def _normalize_position(self, target_model_id, current_position=None):
        last_position = self.get_last_position(target_model_id)
        if current_position is not None:
            last_position -= 1

        if self.position is None:
            return last_position + 1

        return min(max(1, self.position), last_position + 1)

    def __str__(self):
        return "Extra Field"

    def field_type_spec(self):
        try:
            return EXTRA_FIELD_TYPES[self.type]
        except KeyError as e:
            raise RuntimeError(
                f"Extra field {self.internal_name!r} on {self.target_model.model_display_name} has unrecognized type {self.type!r}. " +
                "This may happen if you've downgraded - change the extra field to a supported type."
            ) from e

    def value_of(self, extra_fields_json):
        if extra_fields_json is not None and self.internal_name in extra_fields_json:
            return extra_fields_json[self.internal_name]
        return self.field_type_spec().empty_value()

    def form_field(self, *args, **kwargs):
        return self.field_type_spec().form_field(
            label=self.display_name, help_text=self.description, *args, **kwargs
        )

    def form_widget(self, *args, **kwargs):
        return self.field_type_spec().form_widget(*args, **kwargs)

    def initial_value(self):
        return self.field_type_spec().from_str(self.user_default_value)

    def empty_value(self):
        return self.field_type_spec().empty_value()

    def save(self, *args, **kwargs):
        target_model_id = self.target_model_id or self._target_model_id(self.target_model)
        update_fields = kwargs.get("update_fields")
        must_persist_position = False
        must_persist_target_model = False

        with atomic():
            if self._state.adding:
                self.__class__._lock_target_model(target_model_id)
                self.position = self._normalize_position(target_model_id)
                must_persist_position = True
                self._shift_positions(
                    self.__class__.objects.filter(target_model=target_model_id, position__gte=self.position),
                    1,
                    target_model_id,
                )
            else:
                current = self.__class__.objects.select_for_update().get(pk=self.pk)
                lock_ids = sorted({current.target_model_id, target_model_id})
                for lock_id in lock_ids:
                    self.__class__._lock_target_model(lock_id)

                if current.target_model_id != target_model_id:
                    must_persist_position = True
                    must_persist_target_model = True
                    temp_position = self.get_last_position(current.target_model_id) + 1
                    self.__class__.objects.filter(pk=self.pk).update(position=temp_position)
                    self.__class__._shift_positions(
                        self.__class__.objects.filter(
                            target_model=current.target_model_id,
                            position__gt=current.position,
                        ),
                        -1,
                        current.target_model_id,
                    )
                    self.position = self._normalize_position(target_model_id)
                    self._shift_positions(
                        self.__class__.objects.filter(target_model=target_model_id, position__gte=self.position),
                        1,
                        target_model_id,
                    )
                else:
                    requested_position = self._normalize_position(target_model_id, current.position)

                    if requested_position != current.position:
                        must_persist_position = True
                        temp_position = self.get_last_position(target_model_id) + 1
                        self.__class__.objects.filter(pk=self.pk).update(position=temp_position)

                    if requested_position < current.position:
                        self._shift_positions(
                            self.__class__.objects.filter(
                                target_model=target_model_id,
                                position__gte=requested_position,
                                position__lt=current.position,
                            ),
                            1,
                            target_model_id,
                        )
                    elif requested_position > current.position:
                        self._shift_positions(
                            self.__class__.objects.filter(
                                target_model=target_model_id,
                                position__gt=current.position,
                                position__lte=requested_position,
                            ),
                            -1,
                            target_model_id,
                        )

                    self.position = requested_position

            if update_fields is not None and (must_persist_position or must_persist_target_model):
                update_fields = set(update_fields)
                if must_persist_position:
                    update_fields.add("position")
                if must_persist_target_model:
                    update_fields.add("target_model")
                kwargs["update_fields"] = update_fields

            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        target_model_id = self.target_model_id
        deleted_position = self.position

        with atomic():
            self.__class__._lock_target_model(target_model_id)
            result = super().delete(*args, **kwargs)
            self.__class__._shift_positions(
                self.__class__.objects.filter(target_model=target_model_id, position__gt=deleted_position),
                -1,
                target_model_id,
            )
        return result

    class Meta:
        ordering = ["target_model", F("position").asc(nulls_last=True), "id"]
        verbose_name = "Extra Field"
        unique_together = [("target_model", "internal_name")]
        constraints = [
            models.UniqueConstraint(
                fields=["target_model", "position"],
                name="commandcenter_extrafieldspec_unique_position_per_model",
            ),
            models.CheckConstraint(
                check=Q(position__gte=1) | Q(position__isnull=True),
                name="commandcenter_extrafieldspec_position_gte_1",
            ),
        ]
