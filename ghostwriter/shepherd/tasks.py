"""This contains tasks to be run using Django Q and Redis."""

# Standard Libraries
import datetime
import json
import logging
import logging.config
import traceback
from collections import defaultdict
from datetime import date

# Django Imports
from django.db.models import Q

# 3rd Party Libraries
import boto3
import nmap
import pytz
import requests
from asgiref.sync import async_to_sync
from botocore.exceptions import ClientError
from channels.layers import get_channel_layer
from lxml import objectify

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import (
    CloudServicesConfiguration,
    NamecheapConfiguration,
    SlackConfiguration,
    VirusTotalConfiguration,
)
from ghostwriter.modules.dns_toolkit import DNSCollector
from ghostwriter.modules.review import DomainReview

from .models import (
    Domain,
    DomainNote,
    DomainStatus,
    HealthStatus,
    History,
    ServerHistory,
    ServerStatus,
    StaticServer,
    TransientServer,
    WhoisStatus,
)

# Using __name__ resolves to ghostwriter.shepherd.tasks
logger = logging.getLogger(__name__)

channel_layer = get_channel_layer()


def craft_cloud_message(
    username,
    emoji,
    channel,
    launch_time,
    project_name,
    end_date,
    cloud_provider,
    vps_name,
    ip_address,
    tags,
):
    """
    Craft a nicely formatted Slack message using blocks for cloud asset notifications.
    """
    CLOUD_ASSET_MESSAGE = {
        "username": username,
        "icon_emoji": emoji,
        "channel": channel,
        "text": ":cloud: Teardown Notification for {} :cloud:".format(project_name),
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":cloud: Teardown Notification for {} :cloud:".format(
                        project_name
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Cloud Provider:*\n{}".format(cloud_provider),
                    },
                    {"type": "mrkdwn", "text": "*Instance Name:*\n{}".format(vps_name)},
                    {
                        "type": "mrkdwn",
                        "text": "*Ext IP Address:*\n{}".format(ip_address),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Launch Date:*\n{}".format(launch_time),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Project End Date:*\n{}".format(end_date),
                    },
                    {"type": "mrkdwn", "text": "*Tags:*\n{}".format(tags)},
                ],
            },
        ],
    }
    return json.dumps(CLOUD_ASSET_MESSAGE)


def craft_unknown_asset_message(
    username, emoji, channel, launch_time, cloud_provider, vps_name, ip_address, tags
):
    """
    Craft a nicely formatted Slack message using blocks for cloud assets not found in Ghostwriter.
    """
    UNKNOWN_ASSET_MESSAGE = {
        "username": username,
        "icon_emoji": emoji,
        "channel": channel,
        "text": ":eye: Untracked Cloud Server :eyes:",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":eye: Untracked Cloud Server :eyes:",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "An *untracked* cloud asset is running without being attached to a project. If this asset should be ignored, tag it with one of the configured `Ignore Tags` in settings.",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Cloud Provider:*\n{}".format(cloud_provider),
                    },
                    {"type": "mrkdwn", "text": "*Instance Name:*\n{}".format(vps_name)},
                    {
                        "type": "mrkdwn",
                        "text": "*Ext IP Address:*\n{}".format(ip_address),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Launch Date:*\n{}".format(launch_time),
                    },
                    {"type": "mrkdwn", "text": "*Tags:*\n{}".format(tags)},
                ],
            },
        ],
    }
    return json.dumps(UNKNOWN_ASSET_MESSAGE)


def craft_burned_message(
    username, emoji, channel, domain, categories, burned_explanation
):
    """
    Craft a nicely formatted Slack message using blocks for newly burned domain names.
    """
    BURNED_DOMAIN_MESSAGE = {
        "username": username,
        "icon_emoji": emoji,
        "channel": channel,
        "text": ":fire: Domain Burned :fire:",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":fire: Domain Burned :fire:",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Domain Name:*\n{}".format(domain),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Categories:*\n{}".format(", ".join(categories)),
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(burned_explanation),
                },
            },
        ],
    }
    return json.dumps(BURNED_DOMAIN_MESSAGE)


def craft_warning_message(username, emoji, channel, domain, warning_type, warnings):
    """
    Craft a nicely formatted Slack message using blocks for sending warning nessages.
    """
    WARNING_MESSAGE = {
        "username": username,
        "icon_emoji": emoji,
        "channel": channel,
        "text": ":warning: Domain Event :warning:",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":warning: Domain Event :warning:",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Domain Name:*\n{}".format(domain),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Warning:*\n{}".format(warning_type),
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(warnings),
                },
            },
        ],
    }
    return json.dumps(WARNING_MESSAGE)


class BearerAuth(requests.auth.AuthBase):
    """
    Helper class for providing the ``Authorization`` header with ``Requests``.
    """

    token = None

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = "Bearer " + self.token
        return r


def send_slack_msg(message, slack_channel=None):
    """
    Send a basic Slack message using the global Slack configuration.

    **Parameters**

    ``message``
        A string to be sent as the Slack message
    ``slack_channel``
        Defaults to using the global setting. Can be set to any Slack channel name
    """
    slack_config = SlackConfiguration.get_solo()

    if not slack_channel:
        slack_channel = slack_config.slack_channel

    if slack_config.enable:
        message = slack_config.slack_alert_target + " " + message
        slack_data = {
            "username": slack_config.slack_username,
            "icon_emoji": slack_config.slack_emoji,
            "channel": slack_channel,
            "text": message,
        }
        response = requests.post(
            slack_config.webhook_url,
            data=json.dumps(slack_data),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            logger.warning(
                "Request to Slack returned an error %s, the response was: %s",
                response.status_code,
                response.text,
            )
    else:
        logger.warning(
            "Received request to send Slack message, but Slack notifications are disabled in settings"
        )


def send_slack_complete_msg(task):
    """
    Send a basic Slack message using the global Slack configuration upon completion
    of an ``async_task()``.

    **Parameters**

    ``task``
        Instance of :model:`django_q.Task`
    """
    if task.success:
        send_slack_msg(
            "{} task has completed its run. It completed successfully with no additional result data.".format(
                task.group
            )
        )
    else:
        if task.result:
            send_slack_msg(
                "{} task failed with this result: {}".format(task.group, task.result)
            )
        else:
            send_slack_msg(
                "{} task failed with no result/error data. Check the Django Q admin panel.".format(
                    task.group
                )
            )


def release_domains(no_action=False, reset_dns=False):
    """
    Pull all :model:`shepherd.Domain` currently checked-out in Shepherd and update the
    status to ``Available`` if the project's ``end_date`` value is today or in the past.

    **Parameters**

    ``no_action``
        Set to True to take no action and just return a list of domains that should
        be released (Default: False)
    ``reset_dns``
        Set to True to reset the DNS records for Namecheap domains (Default: False)
    """
    domain_updates = {}
    domain_updates["errors"] = {}

    # Configure Namecheap API requests
    session = requests.Session()
    reset_records_endpoint = "https://api.namecheap.com/xml.response?apiuser={}&apikey={}&username={}&Command=namecheap.domains.dns.setHosts&ClientIp={}&SLD={}&TLD={}"
    reset_record_template = (
        "&HostName1=@&RecordType1=URL&Address1=http://www.namecheap.com&TTL1=100"
    )
    namecheap_config = NamecheapConfiguration.get_solo()
    if reset_dns is True and namecheap_config.enable is False:
        logger.warning(
            "Received request to reset Namecheap DNS records for released domains, but Namecheap API is disabled in settings"
        )

    # Start tracking domain releases
    domains_to_be_released = []

    # First, get all domains set to ``Unavailable``
    queryset = Domain.objects.filter(domain_status__domain_status="Unavailable")

    # Go through each ``Unavailable`` domain and check it against projects
    logger.info("Starting domain release task at %s", datetime.datetime.now())
    for domain in queryset:
        release_me = True
        slack_channel = None
        try:
            # Get latest project checkout for domain
            project_queryset = History.objects.filter(domain__name=domain.name).latest(
                "end_date"
            )
            release_date = project_queryset.end_date
            warning_date = release_date - datetime.timedelta(1)
            if project_queryset.project.slack_channel:
                slack_channel = project_queryset.project.slack_channel
            # Check if date is before or is the end date
            if date.today() <= release_date:
                release_me = False
            # Check if tomorrow is the end date
            if date.today() == warning_date:
                release_me = False
                message = "Your domain, {}, will be released tomorrow! Modify the project's end date as needed.".format(
                    domain.name
                )
                send_slack_msg(message, slack_channel)
        except History.DoesNotExist:
            logger.warning(
                "The domain %s has no project history, so releasing it", domain.name
            )
            release_date = datetime.datetime.today()

        # If ``release_me`` is still ``True``, release the domain
        if release_me:
            logger.warning("The domain %s is marked for release", domain.name)
            domains_to_be_released.append(domain)
            domain_updates[domain.id] = {}
            domain_updates[domain.id]["domain"] = domain.name
            domain_updates[domain.id]["release_date"] = release_date
            # Check no_action and just return list if it is set to True
            if no_action:
                domain_updates[domain.id]["change"] = "no action"
            else:
                logger.info("Releasing %s back into the pool.", domain.name)
                message = "Your domain, {}, has been released.".format(domain.name)
                send_slack_msg(message, slack_channel)
                domain.domain_status = DomainStatus.objects.get(domain_status="Available")
                domain.save()
                domain_updates[domain.id]["change"] = "released"
            # Make sure the Namecheap API config is good and reg is Namecheap
            # Most importantly, check the ``reset_dns`` flag is ``True`` in kwargs
            if (
                namecheap_config.enable
                and domain.registrar.lower() == "namecheap"
                and reset_dns
            ):
                logger.info("Attempting to reset DNS on Namecheap for %s", domain.name)
                try:
                    logger.info(
                        "Attempting to reset DNS on Namecheap for %s", domain.name
                    )
                    # Split domain name for the API call
                    domain_split = domain.name.split(".")
                    sld = domain_split[0]
                    tld = domain_split[1]
                    # The Namecheap API call requires both usernames, a key, and a whitelisted IP
                    req = session.get(
                        reset_records_endpoint.format(
                            namecheap_config.api_username,
                            namecheap_config.api_key,
                            namecheap_config.username,
                            namecheap_config.client_ip,
                            sld,
                            tld,
                        )
                        + reset_record_template
                    )
                    # Check if request returned a 200 OK
                    if req.ok:
                        # Convert Namecheap XML into an easy to use object for iteration
                        root = objectify.fromstring(req.content)
                        # Check the status to make sure it says "OK"
                        namecheap_api_result = root.attrib["Status"]
                        if namecheap_api_result == "OK":
                            is_success = (
                                root.CommandResponse.DomainDNSSetHostsResult.attrib[
                                    "IsSuccess"
                                ]
                            )
                            warnings = (
                                root.CommandResponse.DomainDNSSetHostsResult.Warnings
                            )
                            if is_success == "true":
                                logger.info(
                                    "Successfully reset DNS records for %s", domain.name
                                )
                                domain_updates[domain.id]["dns"] = "reset"
                            else:
                                logger.warning(
                                    'Namecheap did not return True for "IsSuccess" when resetting DNS records for %s',
                                    domain.name,
                                )
                                domain_updates[domain.id]["dns"] = "reset failed"
                        elif namecheap_api_result == "ERROR":
                            error_num = root.Errors.Error.attrib["Number"]
                            error = root.Errors.Error.text
                            logger.error("DNS Error %s: %s", error_num, error)
                            domain_updates[domain.id]["dns"] = "no action"
                            domain_updates["errors"][domain.name] = {}
                            domain_updates["errors"][
                                domain.name
                            ] = "DNS Error {}: {}".format(error_num, error)
                        else:
                            logger.error(
                                'Namecheap did not return an "OK" response – %s',
                                req.text,
                            )
                            domain_updates[domain.id]["dns"] = "no action"
                            domain_updates["errors"][domain.name] = {}
                            domain_updates["errors"][
                                domain.name
                            ] = 'Namecheap did not return an "OK" response.\nFull Response:\n{}'.format(
                                req.text
                            )
                    else:
                        logger.error(
                            'Namecheap API request returned status "%s"',
                            req.status_code,
                        )
                        domain_updates[domain.id]["dns"] = "no action"
                        domain_updates["errors"][domain.name] = {}
                        domain_updates["errors"][
                            domain.name
                        ] = 'Namecheap did not return a 200 response.\nL.. API request returned status "{}"'.format(
                            req.status_code
                        )
                except Exception as error:
                    logger.error("Namecheap API request failed with error: %s", error)
                    domain_updates[domain.id]["dns"] = "no action"
                    domain_updates["errors"][domain.name] = {}
                    domain_updates["errors"][
                        domain.name
                    ] = "Namecheap API request failed with error: {}".format(error)
            else:
                domain_updates[domain.id]["dns"] = "no action"

    logger.info("Domain release task completed at %s", datetime.datetime.now())
    return domain_updates


def release_servers(no_action=False):
    """
    Pull all :model:`shepherd.StaticServer` currently checked-out in Shepherd and
    update the ``server_status`` to ``Available`` if the project's end date is today
    or in the past.

    **Parameters**

    ``no_action``
        Set to True to take no action and just return a list of servers that
        should be released now (Default: False)
    """
    server_updates = {}
    server_updates["errors"] = {}
    servers_to_be_released = []

    # First get all server set to ``Unavailable``
    queryset = StaticServer.objects.filter(server_status__server_status="Unavailable")

    # Go through each ``Unavailable`` server and check it against projects
    for server in queryset:
        release_me = True
        slack_channel = None

        # Get latest project checkout for the server
        try:
            project_queryset = ServerHistory.objects.filter(
                server__ip_address=server.ip_address
            ).latest("end_date")
            release_date = project_queryset.end_date
            warning_date = release_date - datetime.timedelta(1)
            if project_queryset.project.slack_channel:
                slack_channel = project_queryset.project.slack_channel
            # Check if date is before or is the end date
            if date.today() <= release_date:
                release_me = False
            # Check if tomorrow is the end date
            if date.today() == warning_date:
                release_me = False
                message = "Your server, {}, will be released tomorrow! Modify the project's end date as needed.".format(
                    server.ip_address
                )
                send_slack_msg(message, slack_channel)
        except ServerHistory.DoesNotExist:
            logger.warning(
                "The server %s has no project history, so releasing it",
                server.ip_address,
            )
            release_date = datetime.datetime.today()

        # If ``release_me`` is still ``True``, release the server
        if release_me:
            logger.warning("The server %s is marked for release", server.ip_address)
            servers_to_be_released.append(server)
            server_updates[server.id] = {}
            server_updates[server.id]["server"] = server.ip_address
            server_updates[server.id]["hostname"] = server.name
            server_updates[server.id]["release_date"] = release_date

            # Check ``no_action`` and just return list if it is set to ``True``
            if no_action:
                server_updates[server.id]["change"] = "no action"
            else:
                logger.info("Releasing %s back into the pool.", server.ip_address)
                message = "Your server, {}, has been released.".format(server.ip_address)
                send_slack_msg(message, slack_channel)
                server.server_status = ServerStatus.objects.get(server_status="Available")
                server.save()
                server_updates[server.id]["change"] = "released"

    logger.info("Server release task completed at %s", datetime.datetime.now())
    return server_updates


def check_domains(domain=None):
    """
    Initiate a check of all :model:`shepherd.Domain` and update the ``domain_status`` values.

    **Parameters**

    ``domain``
        Individual domain's primary key to update only that domain (Default: None)
    """
    domain_updates = {}
    domain_updates["errors"] = {}

    # Fetch Slack configuration information
    slack_config = SlackConfiguration.get_solo()

    # Get target domain(s) from the database or the target ``domain``
    domain_list = []
    sleep_time_override = None
    if domain:
        try:
            domain_queryset = Domain.objects.get(pk=domain)
            domain_list.append(domain_queryset)
            logger.info(
                "Checking only one domain, so disabling sleep time for VirusTotal"
            )
            sleep_time_override = 0
        except Domain.DoesNotExist:
            domain_updates[domain] = {}
            domain_updates[domain]["change"] = "error"
            domain_updates["errors"][domain.name] = {}
            domain_updates["errors"][
                domain.name
            ] = f"Requested domain ID, {domain}, does not exist"
            logger.exception("Requested domain ID, %s, does not exist", domain)
            return domain_updates
    else:
        # Only fetch domains that are not expired or already burned
        domain_queryset = Domain.objects.filter(
            ~Q(domain_status=DomainStatus.objects.get(domain_status="Expired"))
            & ~Q(health_status=HealthStatus.objects.get(health_status="Burned"))
        )
        for result in domain_queryset:
            domain_list.append(result)

    # Execute ``DomainReview`` to check categories
    domain_review = DomainReview(
        domain_queryset=domain_list, sleep_time_override=sleep_time_override
    )
    lab_results = domain_review.check_domain_status()

    # Update the domains as needed
    for domain in lab_results:
        change = "no action"
        domain_updates[domain.id] = {}
        domain_updates[domain.id]["domain"] = domain.name
        if "vt_results" in lab_results[domain]:
            domain_updates[domain.id]["vt_results"] = lab_results[domain]["vt_results"]
        try:
            # Flip status if a domain has been flagged as burned
            if lab_results[domain]["burned"]:
                domain.health_status = HealthStatus.objects.get(health_status="Burned")
                change = "burned"
                if slack_config.enable:
                    slack_data = craft_burned_message(
                        slack_config.slack_username,
                        slack_config.slack_emoji,
                        slack_config.slack_channel,
                        domain.name,
                        lab_results[domain]["categories"],
                        lab_results[domain]["burned_explanation"],
                    )
                    response = requests.post(
                        slack_config.webhook_url,
                        data=slack_data,
                        headers={"Content-Type": "application/json"},
                    )
            # If the domain isn't marked as burned, check for any informational warnings
            else:
                if lab_results[domain]["warnings"]["total"] > 0:
                    logger.info(
                        "Domain is not burned but there are warnings, so preparing notification"
                    )
                    if slack_config.enable:
                        slack_data = craft_warning_message(
                            slack_config.slack_username,
                            slack_config.slack_emoji,
                            slack_config.slack_channel,
                            domain.name,
                            "VirusTotal Submission",
                            lab_results[domain]["warnings"]["messages"],
                        )
                        response = requests.post(
                            slack_config.webhook_url,
                            data=slack_data,
                            headers={"Content-Type": "application/json"},
                        )
            # Update other fields for the domain object
            if (
                lab_results[domain]["burned"]
                and "burned_explanation" in lab_results[domain]
            ):
                if lab_results[domain]["burned_explanation"]:
                    domain.burned_explanation = "\n".join(
                        lab_results[domain]["burned_explanation"]
                    )
            if lab_results[domain]["categories"] != domain.all_cat:
                change = "categories updated"
            if lab_results[domain]["categories"]:
                domain.all_cat = ", ".join(lab_results[domain]["categories"]).title()
            else:
                domain.all_cat = "Uncategorized"
            domain.last_health_check = datetime.datetime.now()
            domain.save()
            domain_updates[domain.id]["change"] = change
        except Exception:
            trace = traceback.format_exc()
            domain_updates[domain.id]["change"] = "error"
            domain_updates["errors"][domain.name] = {}
            domain_updates["errors"][domain.name] = trace
            logger.exception('Error updating "%s"', domain.name)
            pass

    return domain_updates


def update_dns(domain=None):
    """
    Initiate a check of all :model:`shepherd.Domain` and update each domain's DNS records.

    **Parameters**

    ``domain``
        Individual domain name's primary key to update only that domain (Default: None)
    """
    domain_list = []
    dns_toolkit = DNSCollector()

    domain_updates = {}
    domain_updates["errors"] = {}

    # Get the target domain(s) from the database
    if domain:
        domain_queryset = Domain.objects.get(pk=domain)
        domain_list.append(domain_queryset)
        logger.info(
            "Starting DNS record update for an individual domain %s at %s",
            domain_queryset.name,
            datetime.datetime.now(),
        )
    else:
        logger.info("Starting mass DNS record update at %s", datetime.datetime.now())
        domain_queryset = Domain.objects.filter(
            ~Q(domain_status=DomainStatus.objects.get(domain_status="Expired"))
        )
        for result in domain_queryset:
            domain_list.append(result)

    record_types = ["A", "NS", "MX", "TXT", "CNAME", "SOA", "DMARC"]
    dns_records = dns_toolkit.run_async_dns(
        domains=domain_list, record_types=record_types
    )

    for domain in domain_list:
        domain_updates[domain.id] = {}
        domain_updates[domain.id]["domain"] = domain.name

        if domain.name in dns_records:
            try:
                a_record = dns_records[domain.name]["a_record"]
                mx_record = dns_records[domain.name]["mx_record"]
                ns_record = dns_records[domain.name]["ns_record"]
                txt_record = dns_records[domain.name]["txt_record"]
                soa_record = dns_records[domain.name]["soa_record"]
                cname_record = dns_records[domain.name]["cname_record"]
                dmarc_record = dns_records[domain.name]["dmarc_record"]

                # Format any lists as strings for storage
                if isinstance(a_record, list):
                    a_record = ", ".join(a_record).replace('"', "")
                else:
                    a_record = a_record.replace('"', "")
                if isinstance(mx_record, list):
                    mx_record = ", ".join(mx_record).replace('"', "")
                else:
                    mx_record = mx_record.replace('"', "")
                if isinstance(ns_record, list):
                    ns_record = ", ".join(ns_record).replace('"', "")
                else:
                    ns_record = ns_record.replace('"', "")
                if isinstance(txt_record, list):
                    txt_record = ", ".join(txt_record).replace('"', "")
                else:
                    txt_record = txt_record.replace('"', "")
                if isinstance(soa_record, list):
                    soa_record = ", ".join(soa_record).replace('"', "")
                else:
                    soa_record = soa_record.replace('"', "")
                if isinstance(cname_record, list):
                    cname_record = ", ".join(cname_record).replace('"', "")
                else:
                    cname_record = cname_record.replace('"', "")
                if isinstance(dmarc_record, list):
                    dmarc_record = ", ".join(dmarc_record).replace('"', "")
                else:
                    dmarc_record = dmarc_record.replace('"', "")

                # Assemble the dict to be stored in the database
                dns_records_dict = {}
                dns_records_dict["ns"] = ns_record
                dns_records_dict["a"] = a_record
                dns_records_dict["mx"] = mx_record
                dns_records_dict["cname"] = cname_record
                dns_records_dict["dmarc"] = dmarc_record
                dns_records_dict["txt"] = txt_record
                dns_records_dict["soa"] = soa_record

                # Look-up the individual domain and save the new record string
                domain_instance = Domain.objects.get(name=domain.name)
                domain_instance.dns_record = dns_records_dict
                domain_instance.save()
                domain_updates[domain.id]["result"] = "updated"
            except Exception:
                trace = traceback.format_exc()
                logger.exception("Failed updating DNS records for %s", domain.name)
                domain_updates["errors"][
                    domain.name
                ] = "Failed updating DNS records: {traceback}".format(traceback=trace)
        else:
            logger.warning(
                "The domain %s was not found in the returned DNS records", domain.name
            )
            domain_updates[domain.id]["result"] = "no results"

    # Log task completed
    logger.info("DNS update completed at %s", datetime.datetime.now())
    return domain_updates


def scan_servers(only_active=False):
    """
    Uses ``python-nmap`` to scan individual :model:`shepherd.StaticServer`
    and :model:`shepherd.TransientServer` to identify open ports.

    **Parameters**

    ``only_active``
        Only scan servers marked as in-use (Default: False)
    """
    # Create the scanner
    scanner = nmap.PortScanner()
    # Get the servers stored as static/owned servers
    if only_active:
        server_queryset = StaticServer.objects.filter(
            server_status__server_status="Active"
        )
    else:
        server_queryset = StaticServer.objects.all()
    # Run a scan against each server in tbe queryset
    for server in server_queryset:
        scanner.scan(
            server.ip_address,
            arguments="-sS -Pn -p- -R "
            "--initial-rtt-timeout 100ms "
            "--min-rtt-timeout 100ms "
            "--max-rtt-timeout 200ms "
            "--max-retries 1 "
            "--max-scan-delay 0 --open",
        )
        for host in scanner.all_hosts():
            for proto in scanner[host].all_protocols():
                lport = scanner[host][proto].keys()
                for port in lport:
                    if server.server_status.server_status == "Unavailable":
                        message = "Your server, {}, has an open port - {}".format(
                            host, port
                        )
                        latest = ServerHistory.objects.filter(server=server)[0]
                        if latest.project.slack_channel:
                            send_slack_msg(message, latest.project.slack_channel)
                        else:
                            send_slack_msg(message)


def fetch_namecheap_domains():
    """
    Fetch a list of registered domains for the specified Namecheap account. A valid API key,
    username, and whitelisted IP address must be used. Returns a dictionary containing errors
    and each domain name paired with change status.

    Result status: created, updated, burned, updated & burned

    The returned XML contains entries for domains like this:

    <RequestedCommand>namecheap.domains.getList</RequestedCommand>
    <CommandResponse Type="namecheap.domains.getList">
        <DomainGetListResult>
            <Domain ID='127'
            Name='domain1.com'
            User='owner'
            Created='02/15/2016'
            Expires='02/15/2022'
            IsExpired='False'
            IsLocked='False'
            AutoRenew='False'
            WhoisGuard='ENABLED'
            IsPremium='true'
            IsOurDNS='true'/>
        </DomainGetListResult>
    """
    domains_list = []
    domain_changes = {}
    domain_changes["errors"] = {}
    domain_changes["updates"] = {}
    session = requests.Session()
    get_domain_list_endpoint = "https://api.namecheap.com/xml.response?ApiUser={}&ApiKey={}&UserName={}&Command=namecheap.domains.getList&ClientIp={}&PageSize={}"

    logger.info("Starting Namecheap synchronization task at %s", datetime.datetime.now())

    namecheap_config = NamecheapConfiguration.get_solo()

    try:
        # The Namecheap API call requires both usernames, a key, and a whitelisted IP
        req = session.get(
            get_domain_list_endpoint.format(
                namecheap_config.api_username,
                namecheap_config.api_key,
                namecheap_config.username,
                namecheap_config.client_ip,
                namecheap_config.page_size,
            )
        )
        # Check if request returned a 200 OK
        if req.ok:
            # Convert Namecheap XML into an easy to use object for iteration
            root = objectify.fromstring(req.content)
            # Check the status to make sure it says "OK"
            namecheap_api_result = root.attrib["Status"]
            if namecheap_api_result == "OK":
                # Get all "Domain" node attributes from the XML response
                for domain in root.CommandResponse.DomainGetListResult.Domain:
                    domains_list.append(domain.attrib)
            elif namecheap_api_result == "ERROR":
                error_id = root.Errors[0].Error[0].attrib["Number"]
                error_msg = root.Errors[0].Error[0].text
                logger.error("Namecheap API returned error #%s: %s", error_id, error_msg)
                domain_changes["errors"][
                    "namecheap"
                ] = f"Namecheap API returned error #{error_id}: {error_msg} (see https://www.namecheap.com/support/api/error-codes/)"
                return domain_changes
            else:
                logger.error(
                    'Namecheap did not return an "OK" or "ERROR" response: %s', req.text
                )
                domain_changes["errors"][
                    "namecheap"
                ] = 'Namecheap did not return an "OK" or "ERROR" response: {response}'.format(
                    response=req.text
                )
                return domain_changes
        else:
            logger.error(
                "Namecheap returned a %s response: %s", req.status_code, req.text
            )
            domain_changes["errors"][
                "namecheap"
            ] = "Namecheap returned a {status_code} response: {text}".format(
                status_code=req.status_code, text=req.text
            )
            return domain_changes
    except Exception:
        trace = traceback.format_exc()
        logger.exception("Namecheap API request failed")
        domain_changes["errors"][
            "namecheap"
        ] = "The Namecheap API request failed: {traceback}".format(traceback=trace)
        return domain_changes

    # There's a chance no domains are returned if the provided usernames don't have any domains
    if domains_list:
        # Get the current list of Namecheap domains in the library
        domain_queryset = Domain.objects.filter(registrar="Namecheap")
        expired_status = DomainStatus.objects.get(domain_status="Expired")
        for domain in domain_queryset:
            # Check if a domain in the library is _not_ in the Namecheap response
            if not any(d["Name"] == domain.name for d in domains_list):
                # Domains not found in Namecheap have expired and fallen off the account
                if not domain.expired:
                    logger.info(
                        "Domain %s is not in the Namecheap data so it is now marked as expired",
                        domain.name,
                    )
                    # Mark the domain as Expired
                    domain_changes["updates"][domain.id] = {}
                    domain_changes["updates"][domain.id]["domain"] = domain.name
                    domain_changes["updates"][domain.id]["change"] = "expired"
                    entry = {}
                    domain.expired = True
                    domain.auto_renew = False
                    domain.domain_status = expired_status
                    # If the domain expiration date is in the future, adjust it
                    if domain.expiration >= date.today():
                        domain.expiration = domain.expiration - datetime.timedelta(
                            days=365
                        )
                    try:
                        for attr, value in entry.items():
                            setattr(domain, attr, value)
                        domain.save()
                    except Exception:
                        trace = traceback.format_exc()
                        domain_changes["errors"][
                            domain
                        ] = "Failed to update the entry for {domain}: {traceback}".format(
                            domain=domain, traceback=trace
                        )
                        logger.exception("Failed to update the entry for %s", domain.name)
                        pass
                    instance = DomainNote.objects.create(
                        domain=domain,
                        note="Automatically set to Expired because the domain did not appear in Namecheap during a sync.",
                    )
        # Now, loop over every domain returned by Namecheap
        for domain in domains_list:
            logger.info("Domain %s is now being processed", domain["Name"])

            # Prepare domain attributes for Domain model
            entry = {}
            entry["name"] = domain["Name"]
            entry["registrar"] = "Namecheap"

            # Set the WHOIS status based on WhoisGuard
            if domain["IsExpired"] == "true":
                entry["expired"] = True
                # Expired domains have WhoisGuard set to ``NOTPRESENT``
                entry["whois_status"] = WhoisStatus.objects.get(pk=2)
            else:
                try:
                    entry["whois_status"] = WhoisStatus.objects.get(
                        whois_status__iexact=domain["WhoisGuard"].capitalize()
                    )
                # Anything not ``Enabled`` or ``Disabled``, set to ``Unknown``
                except Exception:
                    logger.exception(
                        "Namecheap WHOIS status (%s) was not found in the database, so defaulted to `Unknown`",
                        domain["WhoisGuard"].capitalize(),
                    )
                    entry["whois_status"] = WhoisStatus.objects.get(pk=3)

            # Check if the domain is locked - locked generally means it's burned
            newly_burned = False
            if domain["IsLocked"] == "true":
                logger.warning(
                    "Domain %s is marked as LOCKED by Namecheap", domain["Name"]
                )
                newly_burned = True
                entry["health_status"] = HealthStatus.objects.get(health_status="Burned")
                entry["domain_status"] = DomainStatus.objects.get(domain_status="Burned")
                entry[
                    "burned_explanation"
                ] = "<p>Namecheap has locked the domain. This is usually the result of a legal complaint related to phishing/malicious activities.</p>"

            # Set AutoRenew status
            if domain["AutoRenew"] == "false":
                entry["auto_renew"] = False

            # Convert Namecheap dates to Django
            entry["creation"] = datetime.datetime.strptime(
                domain["Created"], "%m/%d/%Y"
            ).strftime("%Y-%m-%d")
            entry["expiration"] = datetime.datetime.strptime(
                domain["Expires"], "%m/%d/%Y"
            ).strftime("%Y-%m-%d")

            # Update or create the domain record with assigned attrs
            try:
                instance, created = Domain.objects.update_or_create(
                    name=domain.get("Name"), defaults=entry
                )
                for attr, value in entry.items():
                    setattr(instance, attr, value)

                logger.debug(
                    "Domain %s is being saved with this data: %s", domain["Name"], entry
                )
                instance.save()

                # Add entry to domain change tracking dict
                domain_changes["updates"][instance.id] = {}
                domain_changes["updates"][instance.id]["domain"] = domain["Name"]
                if created and domain["IsLocked"] == "true":
                    domain_changes["updates"][instance.id]["change"] = "created & burned"
                elif created:
                    domain_changes["updates"][instance.id]["change"] = "created"
                else:
                    if newly_burned:
                        domain_changes["updates"][instance.id]["change"] = "burned"
                    else:
                        domain_changes["updates"][instance.id]["change"] = "updated"
            except Exception:
                trace = traceback.format_exc()
                logger.exception(
                    "Encountered an exception while trying to create or update %s",
                    domain["Name"],
                )
                domain_changes["errors"][domain["Name"]] = {}
                domain_changes["errors"][domain["Name"]]["error"] = trace
        logger.info(
            "Namecheap synchronization completed at %s with these changes:\n%s",
            datetime.datetime.now(),
            domain_changes,
        )
    else:
        logger.warning("No domains were returned for the provided Namecheap account!")

    return domain_changes


def months_between(date1, date2):
    """
    Compare two dates and return the number of months beetween them.

    **Parameters**

    ``date1``
        First date for the comparison
    ``date2``
        Second date for the comparison
    """
    if date1 > date2:
        date1, date2 = date2, date1
    m1 = date1.year * 12 + date1.month
    m2 = date2.year * 12 + date2.month
    months = m2 - m1
    if date1.day > date2.day:
        months -= 1
    elif date1.day == date2.day:
        seconds1 = date1.hour * 3600 + date1.minute + date1.second
        seconds2 = date2.hour * 3600 + date2.minute + date2.second
        if seconds1 > seconds2:
            months -= 1
    return months


def json_datetime_converter(dt):
    """
    Convert datetime objects to strings for json.dumps().

    **Parameters**

    ``dt``
        Datetime object to convert to a string

    """
    if isinstance(dt, datetime.datetime):
        return dt.__str__()


def review_cloud_infrastructure(aws_only_running=False):
    """
    Fetch active virtual machines/instances in Digital Ocean, Azure, and AWS and
    compare IP addresses to project infrastructure. Send a report to Slack if any
    instances are still alive after project end date or if an IP address is not found
    for a project.

    Returns a dictionary of cloud assets and encountered errors.

    **Parameters**

    ``aws_only_running``
        Filter out any shutdown AWS resources, where possible (Default: False)
    """
    # Digital Ocean API endpoint for droplets
    DIGITAL_OCEAN_ENDPOINT = "https://api.digitalocean.com/v2/droplets"

    # Fetch cloud API keys and tokens
    cloud_config = CloudServicesConfiguration.get_solo()

    # Fetch Slack configuration information
    slack_config = SlackConfiguration.get_solo()

    # Set timezone for dates to UTC
    utc = pytz.UTC

    # Create info dict
    vps_info = defaultdict()
    vps_info["errors"] = {}
    vps_info["instances"] = {}

    logger.info("Starting review of cloud infrastructure at %s", datetime.datetime.now())

    ###############
    # AWS Section #
    ###############

    # Create AWS client for EC2 using a default region and get a list of all regions
    aws_capable = True
    regions = []
    try:
        client = boto3.client(
            "ec2",
            region_name="us-west-2",
            aws_access_key_id=cloud_config.aws_key,
            aws_secret_access_key=cloud_config.aws_secret,
        )
        regions = [
            region["RegionName"] for region in client.describe_regions()["Regions"]
        ]
    except ClientError:
        logger.error("AWS could not validate the provided credentials for EC2")
        aws_capable = False
        vps_info["errors"][
            "aws"
        ] = "AWS could not validate the provided credentials for EC2"
    except Exception:
        trace = traceback.format_exc()
        logger.exception("Testing authentication to AWS failed")
        aws_capable = False
        vps_info["errors"][
            "aws"
        ] = "Testing authentication to AWS EC2 failed: {traceback}".format(
            traceback=trace
        )
    if aws_capable:
        logger.info("AWS credentials are functional for EC2, beginning AWS review")
        # Loop over the regions to check each one for EC2 instances
        for region in regions:
            logger.info("Checking AWS region %s", region)
            # Create an EC2 resource for the region
            ec2 = boto3.resource(
                "ec2",
                region_name=region,
                aws_access_key_id=cloud_config.aws_key,
                aws_secret_access_key=cloud_config.aws_secret,
            )
            # Get all EC2 instances that are running
            if aws_only_running:
                running_instances = ec2.instances.filter(
                    Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                )
            else:
                running_instances = ec2.instances.all()
            # Loop over running instances to generate info dict
            for instance in running_instances:
                # Calculate how long the instance has been running in UTC
                time_up = months_between(
                    instance.launch_time.replace(tzinfo=utc),
                    datetime.datetime.today().replace(tzinfo=utc),
                )
                tags = []
                name = "Blank"
                if instance.tags:
                    for tag in instance.tags:
                        # AWS assigns names to instances via a ``Name`` key`
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                        else:
                            tags.append("{}: {}".format(tag["Key"], tag["Value"]))
                pub_addresses = []
                pub_addresses.append(instance.public_ip_address)
                priv_addresses = []
                priv_addresses.append(instance.private_ip_address)
                # Add instance info to a dictionary
                vps_info["instances"][instance.id] = {
                    "id": instance.id,
                    "provider": "Amazon Web Services {}".format(region),
                    "service": "EC2",
                    "name": name,
                    "type": instance.instance_type,
                    "monthly_cost": None,  # AWS cost is different and not easily calculated
                    "cost_to_date": None,  # AWS cost is different and not easily calculated
                    "state": instance.state["Name"],
                    "private_ip": priv_addresses,
                    "public_ip": pub_addresses,
                    "launch_time": instance.launch_time.replace(tzinfo=utc),
                    "time_up": "{} months".format(time_up),
                    "tags": ", ".join(tags),
                }

    ###############
    # DO Section  #
    ###############

    # Get all Digital Ocean droplets for the account
    active_droplets = {}
    do_capable = True
    headers = {"Content-Type": "application/json"}
    try:
        active_droplets = requests.get(
            DIGITAL_OCEAN_ENDPOINT,
            headers=headers,
            auth=BearerAuth(cloud_config.do_api_key),
        )
        if active_droplets.status_code == 200:
            active_droplets = active_droplets.json()
            logger.info(
                "Digital Ocean credentials are functional, beginning droplet review"
            )
        else:
            do_capable = False
            logger.info(
                "Digital Ocean denied access with HTTP code %s and this message: %s",
                active_droplets.status_code,
                active_droplets.text,
            )
            try:
                error_message = active_droplets.json()
                api_response = error_message
                if "message" in error_message:
                    api_response = error_message["message"]
            except ValueError:
                api_response = active_droplets.text
            vps_info["errors"][
                "digital_ocean"
            ] = f"Digital Ocean API request failed with this response: {api_response}"
    # Catch a JSON decoding error with the response
    except ValueError:
        logger.exception("Could not decode the response from Digital Ocean")
        do_capable = False
        vps_info["errors"][
            "digital_ocean"
        ] = f"Could not decode this response from Digital Ocean: {active_droplets.text}"
    # Catch any other errors related to the web request
    except Exception:
        trace = traceback.format_exc()
        logger.exception(
            "Could not retrieve content from Digital Ocean with the provided API key"
        )
        do_capable = False
        vps_info["errors"][
            "digital_ocean"
        ] = "Could not retrieve content from Digital Ocean with the provided API key: {traceback}".format(
            traceback=trace
        )
    # Loop over the droplets to generate the info dict
    if do_capable and "droplets" in active_droplets:
        for droplet in active_droplets["droplets"]:
            # Get the networking info
            if "v4" in droplet["networks"]:
                ipv4 = droplet["networks"]["v4"]
            else:
                ipv4 = []
            if "v6" in droplet["networks"]:
                ipv6 = droplet["networks"]["v6"]
            else:
                ipv6 = []
            # Create lists of public and private addresses
            pub_addresses = []
            priv_addresses = []
            for address in ipv4:
                if address["type"] == "private":
                    priv_addresses.append(address["ip_address"])
                else:
                    pub_addresses.append(address["ip_address"])
            for address in ipv6:
                if address["type"] == "private":
                    priv_addresses.append(address["ip_address"])
                else:
                    pub_addresses.append(address["ip_address"])
            # Calculate how long the instance has been running in UTC and cost to date
            time_up = months_between(
                datetime.datetime.strptime(
                    droplet["created_at"].split("T")[0], "%Y-%m-%d"
                ).replace(tzinfo=utc),
                datetime.datetime.today().replace(tzinfo=utc),
            )
            cost_to_date = (
                months_between(
                    datetime.datetime.strptime(
                        droplet["created_at"].split("T")[0], "%Y-%m-%d"
                    ),
                    datetime.datetime.today(),
                )
                * droplet["size"]["price_monthly"]
            )
            # Add an entry to the dict for the droplet
            vps_info["instances"][droplet["id"]] = {
                "id": droplet["id"],
                "provider": "Digital Ocean",
                "service": "Droplets",
                "name": droplet["name"],
                "type": droplet["image"]["distribution"] + " " + droplet["image"]["name"],
                "monthly_cost": droplet["size"]["price_monthly"],
                "cost_to_date": cost_to_date,
                "state": droplet["status"],
                "private_ip": priv_addresses,
                "public_ip": pub_addresses,
                "launch_time": datetime.datetime.strptime(
                    droplet["created_at"].split("T")[0], "%Y-%m-%d"
                ).replace(tzinfo=utc),
                "time_up": "{} months".format(time_up),
                "tags": ", ".join(droplet["tags"]),
            }
    # Examine results to identify potentially unneeded/unused machines
    assets_in_use = []
    for instance_id, instance in vps_info["instances"].items():
        all_ip_addresses = []
        for address in instance["public_ip"]:
            all_ip_addresses.append(address)
        for address in instance["private_ip"]:
            all_ip_addresses.append(address)
        # Set instance's name to its ID if no name is set
        if instance["name"]:
            instance_name = instance["name"]
        else:
            instance_name = instance["id"]
        # Check if any IP address is associated with a project
        queryset = TransientServer.objects.select_related("project").filter(
            ip_address__in=all_ip_addresses
        )
        if queryset:
            for result in queryset:
                # Consider the asset in use if the project's end date is in the past
                if result.project.end_date < date.today():
                    logger.info(
                        "Project end date is %s which is earlier than now, %s",
                        result.project.end_date,
                        datetime.datetime.now().date(),
                    )
                    if slack_config.enable:
                        if result.project.slack_channel:
                            slack_data = craft_cloud_message(
                                slack_config.slack_username,
                                slack_config.slack_emoji,
                                result.project.slack_channel,
                                instance["launch_time"],
                                result.project,
                                result.project.end_date,
                                instance["provider"],
                                instance_name,
                                ", ".join(instance["public_ip"]),
                                instance["tags"],
                            )
                            response = requests.post(
                                slack_config.webhook_url,
                                data=slack_data,
                                headers={"Content-Type": "application/json"},
                            )
                        else:
                            slack_data = craft_cloud_message(
                                slack_config.slack_username,
                                slack_config.slack_emoji,
                                slack_config.slack_channel,
                                instance["launch_time"],
                                result.project,
                                result.project.end_date,
                                instance["provider"],
                                instance_name,
                                ", ".join(instance["public_ip"]),
                                instance["tags"],
                            )
                            response = requests.post(
                                slack_config.webhook_url,
                                data=slack_data,
                                headers={"Content-Type": "application/json"},
                            )
                else:
                    # Project is still active, so track these assets for later
                    assets_in_use.append(instance_id)
        else:
            ignore_tags = []
            instance_tags = []
            for tag in cloud_config.ignore_tag.split(","):
                ignore_tags.append(tag.strip())
            for tag in instance["tags"].split(","):
                instance_tags.append(tag.strip())
            if any(tag in ignore_tags for tag in instance_tags):
                logger.info(
                    "Ignoring %s because it is tagged with a configured ignore tag",
                    instance_name,
                )
                assets_in_use.append(instance_id)
            else:
                if slack_config.enable:
                    slack_data = craft_unknown_asset_message(
                        slack_config.slack_username,
                        slack_config.slack_emoji,
                        slack_config.slack_channel,
                        instance["launch_time"],
                        instance["provider"],
                        instance_name,
                        ", ".join(instance["public_ip"]),
                        instance["tags"],
                    )
                    response = requests.post(
                        slack_config.webhook_url,
                        data=slack_data,
                        headers={"Content-Type": "application/json"},
                    )

    # Return the stale cloud asset data in JSON for the task results
    json_data = json.dumps(dict(vps_info), default=json_datetime_converter, indent=2)
    logger.info("Cloud review completed at %s", datetime.datetime.now())
    logger.info("JSON results:\n%s", json_data)
    return json_data


def check_expiration():
    """
    Update expiration status for all :model:`shepherd.Domain`.
    """
    domain_changes = {}
    domain_changes["errors"] = {}
    domain_changes["updates"] = {}
    expired_status = DomainStatus.objects.get(domain_status="Expired")
    domain_queryset = Domain.objects.filter(~Q(domain_status=expired_status))
    for domain in domain_queryset:
        logger.info("Checking expiration status of %s", domain)
        domain_changes["updates"][domain.id] = {}
        domain_changes["updates"][domain.id]["change"] = "no change"
        if domain.expiration <= date.today():
            domain_changes["updates"][domain.id]["domain"] = domain.name
            # If the domain is set to auto-renew, update the expiration date
            if domain.auto_renew:
                logger.info("Adding one year to %s's expiration date", domain.name)
                domain_changes["updates"][domain.id]["change"] = "auto-renewed"
                domain.expiration = domain.expiration + datetime.timedelta(days=365)
                domain.expired = False
                domain.save()
            # Otherwise, mark the domain as expired
            else:
                logger.info(
                    "Expiring domain %s due to expiration date, %s",
                    domain.name,
                    domain.expiration,
                )
                domain_changes["updates"][domain.id]["change"] = "expired"
                domain.expired = True
                domain.domain_status = expired_status
                domain.save()

    logger.info("Domain expiration update completed at %s", datetime.datetime.now())
    return domain_changes


def test_aws_keys(user):
    """
    Test the AWS access keys configured in :model:`commandcenter.CloudServicesConfiguration`.
    """
    cloud_config = CloudServicesConfiguration.get_solo()
    level = "error"
    logger.info("Starting a test of the AWS keys at %s", datetime.datetime.now())
    try:
        # Send the STS ``get_caller_identity`` API call to test keys
        client = boto3.client(
            "sts",
            region_name="us-west-2",
            aws_access_key_id=cloud_config.aws_key,
            aws_secret_access_key=cloud_config.aws_secret,
        )
        client.get_caller_identity()
        logger.info("Successfully verified the AWS keys")
        message = "Successfully verified the AWS keys"
        level = "success"
    except ClientError:
        logger.error("AWS could not validate the provided credentials")
        message = "AWS could not validate the provided credentials"
    except Exception:
        logger.exception("Testing authentication to AWS failed")
        message = "Testing authentication to AWS failed"

    # Send a message to the requesting user
    async_to_sync(channel_layer.group_send)(
        "notify_{}".format(user),
        {
            "type": "message",
            "message": {
                "message": message,
                "level": level,
                "title": "AWS Test Complete",
            },
        },
    )

    logger.info("Test of the AWS access keys completed at %s", datetime.datetime.now())
    return {"result": level, "message": message}


def test_digital_ocean(user):
    """
    Test the Digital Ocean API key configured in
    :model:`commandcenter.CloudServicesConfiguration`.
    """
    DIGITAL_OCEAN_ENDPOINT = "https://api.digitalocean.com/v2/droplets"
    cloud_config = CloudServicesConfiguration.get_solo()
    level = "error"
    logger.info(
        "Starting a test of the Digital Ocean API key at %s", datetime.datetime.now()
    )
    try:
        # Request all active droplets (as done in the real task)
        headers = {"Content-Type": "application/json"}
        active_droplets = requests.get(
            DIGITAL_OCEAN_ENDPOINT,
            headers=headers,
            auth=BearerAuth(cloud_config.do_api_key),
        )
        if active_droplets.status_code == 200:
            logger.info(
                "Digital Ocean credentials are functional, beginning droplet review"
            )
            logger.info("Successfully verified the Digital Ocean API key")
            message = "Successfully verified the Digital Ocean API key"
            level = "success"
        else:
            logger.info(
                "Digital Ocean denied access with HTTP code %s and this message: %s",
                active_droplets.status_code,
                active_droplets.text,
            )
            api_response = active_droplets.text
            try:
                error_message = active_droplets.json()
                if "message" in error_message:
                    api_response = error_message["message"]
            except ValueError:
                pass
            message = f"Digital Ocean denied access with HTTP code {active_droplets.status_code} and this message: {api_response}"
    except ClientError:
        logger.error("Digital Ocean could not validate the provided API key")
        message = "Digital Ocean could not validate the provided API key"
    except Exception:
        logger.exception("Testing authentication to Digital Ocean failed")
        message = "Testing authentication to Digital Ocean failed"

    # Send a message to the requesting user
    async_to_sync(channel_layer.group_send)(
        "notify_{}".format(user),
        {
            "type": "message",
            "message": {
                "message": message,
                "level": level,
                "title": "Digital Ocean Test Complete",
            },
        },
    )

    logger.info(
        "Test of the Digital Ocean API key completed at %s", datetime.datetime.now()
    )
    return {"result": level, "message": message}


def test_namecheap(user):
    """
    Test the Namecheap API configuration stored in :model:`commandcenter.NamecheapConfiguration`.
    """
    session = requests.Session()
    get_domain_list_endpoint = "https://api.namecheap.com/xml.response?ApiUser={}&ApiKey={}&UserName={}&Command=namecheap.domains.getList&ClientIp={}&PageSize={}"
    namecheap_config = NamecheapConfiguration.get_solo()
    level = "error"
    logger.info("Starting Namecheap API test at %s", datetime.datetime.now())
    try:
        # The Namecheap API call requires both usernames, a key, and a whitelisted IP
        req = session.get(
            get_domain_list_endpoint.format(
                namecheap_config.api_username,
                namecheap_config.api_key,
                namecheap_config.username,
                namecheap_config.client_ip,
                namecheap_config.page_size,
            )
        )
        # Check if request returned a 200 OK
        if req.ok:
            # Convert Namecheap XML into an easy to use object for iteration
            root = objectify.fromstring(req.content)
            # Check the status to make sure it says "OK"
            namecheap_api_result = root.attrib["Status"]
            if namecheap_api_result == "OK":
                level = "success"
                message = "Successfully authenticated to Namecheap"
            elif namecheap_api_result == "ERROR":
                error_id = root.Errors[0].Error[0].attrib["Number"]
                error_msg = root.Errors[0].Error[0].text
                logger.error("Namecheap API returned error #%s: %s", error_id, error_msg)
                message = f"Namecheap API returned error #{error_id}: {error_msg} (see https://www.namecheap.com/support/api/error-codes/)"
            else:
                logger.error(
                    "Namecheap did not return an response: %s",
                    namecheap_api_result,
                    req.text,
                )
                message = (
                    "Namecheap returned a {namecheap_api_result} response: {req.text}"
                )
        else:
            logger.error(
                "Namecheap returned HTTP code %s in its response: %s",
                req.status_code,
                req.text,
            )
            message = f"Namecheap returned HTTP code {req.status_code} in its response: {req.text}"
    except Exception:
        trace = traceback.format_exc()
        logger.exception("Namecheap API request failed")
        message = f"The Namecheap API request failed: {trace}"

    # Send a message to the requesting user
    async_to_sync(channel_layer.group_send)(
        "notify_{}".format(user),
        {
            "type": "message",
            "message": {
                "message": message,
                "level": level,
                "title": "Namecheap Test Complete",
            },
        },
    )

    logger.info(
        "Test of the Namecheap API configuration completed at %s",
        datetime.datetime.now(),
    )
    return {"result": level, "message": message}


def test_slack_webhook(user):
    """
    Test the Slack Webhook configuration stored in :model:`commandcenter.SlackConfiguration`.
    """
    slack_config = SlackConfiguration.get_solo()
    level = "error"
    logger.info("Starting Slack Webhook test at %s", datetime.datetime.now())
    try:
        if slack_config.enable:
            slack_data = {
                "username": slack_config.slack_username,
                "icon_emoji": slack_config.slack_emoji,
                "channel": slack_config.slack_channel,
                "text": f"{slack_config.slack_alert_target} Hello from Ghostwriter :wave:",
            }
            response = requests.post(
                slack_config.webhook_url,
                data=json.dumps(slack_data),
                headers={"Content-Type": "application/json"},
            )
            if response.ok:
                level = "success"
                message = f"Slack accepted the request and you should see a message posted in {slack_config.slack_channel}"
            elif response.status_code == 400:
                message = f"Slack accepted the request, but said the user {slack_config.slack_channel} does not exist"
            elif response.status_code == 403:
                if "invalid_token" in response.text:
                    message = "Slack accepted the request, but said your Webhook token is invalid"
                elif "action_prohibited" in response.text:
                    message = f"Slack accepted the request, but said your Webhook token cannot send messages to {slack_config.slack_channel}, or is otherwise restricted"
                else:
                    message = f"Slack accepted the request, but said your Webhook token is not permitted to send messages"
            elif response.status_code == 404:
                if "channel_not_found" in response.text:
                    message = f"Slack accepted the request, but said it could not find the {slack_config.slack_channel} channel"
                else:
                    message = f"Slack accepted the request, but said it could not find the {slack_config.slack_channel} channel"
            elif response.status_code == 410:
                if "channel_is_archived" in response.text:
                    message = f"Slack accepted the request, but said the {slack_config.slack_channel} channel is archived"
                else:
                    message = f"Slack accepted the request, but said the {slack_config.slack_channel} channel is unavailable - possibly archived?"
            else:
                logger.warning(
                    "Request to Slack returned HTTP code %s with this message: %s",
                    response.status_code,
                    response.text,
                )
                message = f"Request to Slack returned HTTP code {response.status_code} with this message: {response.text}"
        else:
            logger.warning(
                "Received request to send Slack message, but Slack notifications are disabled in settings"
            )
            message = "Received request to send Slack message, but Slack notifications are disabled in settings"
    except Exception:
        trace = traceback.format_exc()
        logger.exception("Slack Webhook API request failed")
        message = f"Slack Webhook API request failed: {trace}"

    # Send a message to the requesting user
    async_to_sync(channel_layer.group_send)(
        "notify_{}".format(user),
        {
            "type": "message",
            "message": {
                "message": message,
                "level": level,
                "title": "Slack Test Complete",
            },
        },
    )

    logger.info("Test of the Slack Webhook completed at %s", datetime.datetime.now())
    return {"result": level, "message": message}


def test_virustotal(user):
    """
    Test the VirusTotal API key stored in :model:`commandcenter.VirusTotalConfiguration`.
    """
    virustotal_config = VirusTotalConfiguration.get_solo()
    level = "error"
    logger.info("Starting VirusTotal API test at %s", datetime.datetime.now())
    try:
        if virustotal_config.enable:
            virustotal_url = "https://www.virustotal.com/vtapi/v2/url/report"
            params = {"apikey": virustotal_config.api_key, "resource": "google.com"}
            response = requests.get(virustotal_url, params=params)
            logger.info(response.status_code)

            if response.ok:
                message = "Successfully authenticated to the VirusTotal API"
                level = "success"
                logger.info("VT Test Succeeded")
            elif response.status_code == 204:
                message = "Successfully authenticated to the VirusTotal API, but response indicated the API key has hit its rate limit for now"
                level = "warning"
            elif response.status_code == 400:
                message = "VirusTotal did not accept the API request (Bad Request)"
            elif response.status_code == 403:
                message = "Successfully authenticated to the VirusTotal API, but response indicated the configured key is restricted"
                level = "warning"
            else:
                logger.warning(
                    "Request to VirusTotal API returned HTTP code %s with this message: %s",
                    response.status_code,
                    response.text,
                )
                message = f"Request to VirusTotal API returned HTTP code {response.status_code} with this message: {response.text}"
        else:
            logger.warning(
                "Received request to test the VirusTotal API key, but VirusTotal is disabled in settings"
            )
            message = "Received request to test the VirusTotal API key, but VirusTotal is disabled in settings"
    except Exception:
        trace = traceback.format_exc()
        logger.exception("VirusTotal API request failed")
        message = f"VirusTotal API request failed: {trace}"

    # Send a message to the requesting user
    async_to_sync(channel_layer.group_send)(
        "notify_{}".format(user),
        {
            "type": "message",
            "message": {
                "message": message,
                "level": level,
                "title": "VirusTotal Test Complete",
            },
        },
    )

    logger.info("Test of the VirusTotal completed at %s", datetime.datetime.now())
    return {"result": level, "message": message}
