"""This contains tasks to be run using Django Q and Redis."""


# Import the shepherd application's models and settings
from django.db.models import Q
from django.conf import settings
from django.core.files import File

from .models import (Domain, History, DomainStatus, HealthStatus,
    StaticServer, ServerStatus, ServerHistory, WhoisStatus,
    TransientServer, DomainNote)

# Import Python libraries for various things
import io
import os
import json
import pytz
import nmap
import boto3
import zipfile
import requests
import datetime
from datetime import date
from lxml import objectify
from collections import defaultdict
from botocore.exceptions import ClientError

# Import custom modules
from ghostwriter.modules.dns import DNSCollector
from ghostwriter.modules.review import DomainReview


# Setup logger
import logging
import logging.config

# Using __name__ resolves to ghostwriter.shepherd.tasks
logger = logging.getLogger(__name__)
LOGGING_CONFIG = None
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            # Format: timestamp + name + 12 spaces + info level + 8 spaces + message
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'loggers': {
        '': {
            'level': 'INFO',
            'handlers': ['console'],
        },
    },
})


def craft_cloud_message(
    username, emoji, channel, launch_time, project_name, end_date,
    cloud_provider, vps_name, tags
):
    """Function to craft a nicely formatted Slack message using blocks
    for cloud asset notifications.
    """
    CLOUD_ASSET_MESSAGE = {
        "username": username,
        "icon_emoji": emoji,
        "channel": channel,
        "text": "A cloud asset for this project looks like it is ready to be torn down:\n*{}*".format(project_name),
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "A cloud asset for this project looks like it is ready to be torn down:\n*{}*".format(project_name)
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Cloud Provider:*\n{}".format(cloud_provider)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Instance Name:*\n{}".format(vps_name)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Launch Date:*\n{}".format(launch_time)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Project End Date:*\n{}".format(end_date)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Tags:*\n{}".format(tags)
                    }
                ]
            }
        ]
    }
    return json.dumps(CLOUD_ASSET_MESSAGE)


def craft_unknown_asset_message(
    username, emoji, channel, launch_time, cloud_provider, vps_name, tags
):
    """Function to craft a nicely formatted Slack message using blocks
    for cloud assets not found in Ghostwriter.
    """
    UNKNOWN_ASSET_MESSAGE = {
        "username": username,
        "icon_emoji": emoji,
        "channel": channel,
        "text": "An *untracked* cloud asset is running without being attached to a project. If this asset should be ignored, add the `gw_ignore` tag.",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "An *untracked* cloud asset is running without being attached to a project. If this asset should be ignored, add the `gw_ignore` tag.",
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Cloud Provider:*\n{}".format(cloud_provider)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Instance Name:*\n{}".format(vps_name)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Launch Date:*\n{}".format(launch_time)
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Tags:*\n{}".format(tags)
                    }
                ]
            }
        ]
    }
    return json.dumps(UNKNOWN_ASSET_MESSAGE)


def get_slack_config():
    """Function to determine if Slack settings are configured and return the
    settings if available.
    """
    try:
        enable_slack = settings.SLACK_CONFIG['enable_slack']
    except KeyError:
        enable_slack = False
        return enable_slack
    if enable_slack:
        try:
            slack_config = {}
            slack_config['slack_emoji'] = settings.SLACK_CONFIG['slack_emoji']
            slack_config['slack_username'] = settings.SLACK_CONFIG['slack_username']
            slack_config['slack_webhook_url'] = settings.SLACK_CONFIG['slack_webhook_url']
            slack_config['slack_alert_target'] = settings.SLACK_CONFIG['slack_alert_target']
            slack_config['slack_channel'] = settings.SLACK_CONFIG['slack_channel']
            slack_capable = True
        except KeyError:
            slack_capable = False
        return slack_config
    else:
        return enable_slack


class BearerAuth(requests.auth.AuthBase):
    """Helper class for providing the Authorization header with Requests."""
    token = None
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["Authorization"] = "Bearer " + self.token
        return r


def send_slack_msg(message, slack_channel=None):
    """Accepts message text and sends it to Slack. This requires Slack
    settings and a webhook be configured in the application's settings.

    Parameters:

    message         A string to be sent as the Slack message
    slack_channel   Defaults to using the global setting. Can be set to any
                    Slack channel name.
    """
    try:
        enable_slack = settings.SLACK_CONFIG['enable_slack']
    except KeyError:
        enable_slack = False
    if enable_slack:
        try:
            slack_emoji = settings.SLACK_CONFIG['slack_emoji']
            slack_username = settings.SLACK_CONFIG['slack_username']
            slack_webhook_url = settings.SLACK_CONFIG['slack_webhook_url']
            slack_alert_target = settings.SLACK_CONFIG['slack_alert_target']
            if not slack_channel:
                slack_channel = settings.SLACK_CONFIG['slack_channel']
            slack_capable = True
        except KeyError:
            slack_capable = False

        if slack_capable:
            message = slack_alert_target + ' ' + message
            slack_data = {
                'username': slack_username,
                'icon_emoji': slack_emoji,
                'channel': slack_channel,
                'text': message
            }
            response = requests.post(slack_webhook_url,
                                     data=json.dumps(slack_data),
                                     headers={'Content-Type':
                                              'application/json'})
            if response.status_code != 200:
                logger.error(
                    'Request to Slack returned an error %s, the response is:\n%s',
                    response.status_code,
                    response.text
                    )


def send_slack_test_msg(slack_channel=None):
    """Use `send_slack_msg` to send a test message using the configured Slack webhook."""
    message = "This is a test of your notification system."
    send_slack_msg(message, slack_channel)


def send_slack_complete_msg(task):
    """Function to send a Slack message for a task. Meant to be used as a hook
    for an async_task().
    """
    if task.success:
        send_slack_msg('{} task has completed its run. It completed '
                       'successfully with no additional result data.'.
                       format(task.group))
    else:
        if task.result:
            send_slack_msg('{} task failed with this result: {}'.
                           format(task.group, task.result))
        else:
            send_slack_msg('{} task failed with no result/error data. Check '
                           'the Django Q admin panel.'.format(task.group))


def release_domains(no_action=False, reset_dns=False):
    """Pull all domains currently checked-out in Shepherd and update the
    status to Available if the project's end date is today or in the past.

    Parameters:

    no_action       Defaults to False. Set to True to take no action and just
                    return a list of domains that should be released now.
    reset_dns       Defaults to False. Set to True to reset the DNS records for
                    Namecheap domains. This sets the DNS records to the defaults.
    """
    domain_updates = {}
    domain_updates['errors'] = {}
    # Configure Namecheap API requests
    namecheap_ready = False
    session = requests.Session()
    reset_records_endpoint = 'https://api.namecheap.com/xml.response?apiuser={}&apikey={}&username={}&Command=namecheap.domains.dns.setHosts&ClientIp={}&SLD={}&TLD={}'
    reset_record_template = '&HostName1=@&RecordType1=URL&Address1=http://www.namecheap.com&TTL1=100'
    try:
        client_ip = settings.NAMECHEAP_CONFIG['client_ip']
        enable_namecheap = settings.NAMECHEAP_CONFIG['enable_namecheap']
        namecheap_api_key = settings.NAMECHEAP_CONFIG['namecheap_api_key']
        namecheap_username = settings.NAMECHEAP_CONFIG['namecheap_username']
        namecheap_api_username = settings.NAMECHEAP_CONFIG['namecheap_api_username']
        namecheap_ready = True
        logger.info('Successfully pulled Namecheap API configuration')
    except KeyError as error:
        logger.error('Could not retrieve API configuration: %s', error)
        domain_updates['errors']['namecheap'] = 'Could not retrieve API configuration: {}'.format(error)
    # Start tracking domain releases
    domains_to_be_released = []
    # First, get all domains set to `Unavailable`
    queryset = Domain.objects.\
        filter(domain_status__domain_status='Unavailable')
    # Go through each `Unavailable` domain and check it against projects
    logger.info('Starting domain release task at %s', datetime.datetime.now())
    for domain in queryset:
        # Get all projects for the domain
        release_me = True
        slack_channel = None
        try:
            project_queryset = History.objects.filter(domain__name=domain.name).latest('end_date')
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
                message = "Your domain, {}, will be released tomorrow! " \
                        "Modify the project's end date as needed.".\
                        format(domain.name)
                if project_queryset.project.slack_channel:
                    send_slack_msg(message, project_queryset.project.slack_channel)
                else:
                    send_slack_msg(message)
        except History.DoesNotExist:
            logger.warning('The domain %s has no project history, so releasing it', domain.name)
            release_date = datetime.datetime.today()
        # If release_me is still true, release the domain
        if release_me:
            logger.warning('The domain %s is marked for release', domain.name)
            domains_to_be_released.append(domain)
            domain_updates[domain.id] = {}
            domain_updates[domain.id]['domain'] = domain.name
            domain_updates[domain.id]['release_date'] = release_date
            # Check no_action and just return list if it is set to True
            if no_action:
                domain_updates[domain.id]['change'] = 'no action'
            else:
                message = 'Your domain, {}, has been released.'.format(domain.name)
                if slack_channel:
                    send_slack_msg(message, slack_channel)
                else:
                    send_slack_msg(message)
                domain.domain_status = DomainStatus.objects.\
                    get(domain_status='Available')
                # domain.save()
                domain_updates[domain.id]['change'] = 'released'
            # Make sure the Namecheap API config is good and reg is Namecheap
            # Most importantly, check the `reset_dns` flag is True in kwargs
            if namecheap_ready and domain.registrar.lower() == 'namecheap' and reset_dns:
                logger.info('Attempting to reset DNS on Namecheap for %s', domain.name)
                try:
                    logger.info('Attempting to reset DNS on Namecheap for %s', domain.name)
                    # Split domain name for the API call
                    domain_split = domain.name.split('.')
                    sld = domain_split[0]
                    tld = domain_split[1]
                    # The Namecheap API call requires both usernames, a key, and a whitelisted IP
                    req = session.get(
                        reset_records_endpoint.format(
                            namecheap_api_username, namecheap_api_key, namecheap_username,
                            client_ip, sld, tld) + reset_record_template)
                    # Check if request returned a 200 OK
                    if req.ok:
                        # Convert Namecheap XML into an easy to use object for iteration
                        root = objectify.fromstring(req.content)
                        # Check the status to make sure it says "OK"
                        namecheap_api_result = root.attrib['Status']
                        if namecheap_api_result == 'OK':
                            is_success = root.CommandResponse.DomainDNSSetHostsResult.attrib['IsSuccess']
                            warnings = root.CommandResponse.DomainDNSSetHostsResult.Warnings
                            if is_success == 'true':
                                logger.info('Successfully reset DNS records for %s', domain.name)
                                domain_updates[domain.id]['dns'] = 'reset'
                            else:
                                logger.warning('Namecheap did not return True for "IsSuccess" when resetting DNS records for %s', domain.name)
                                domain_updates[domain.id]['dns'] = 'reset failed'
                        elif namecheap_api_result == 'ERROR':
                            error_num = root.Errors.Error.attrib['Number']
                            error = root.Errors.Error.text
                            logger.error('DNS Error %s: %s', error_num, error)
                            domain_updates[domain.id]['dns'] = 'no action'
                            domain_updates['errors'][domain.name] = {}
                            domain_updates['errors'][domain.name] = 'DNS Error {}: {}'.format(error_num, error)
                        else:
                            logger.error('Namecheap did not return an "OK" response – %s', req.text)
                            domain_updates[domain.id]['dns'] = 'no action'
                            domain_updates['errors'][domain.name] = {}
                            domain_updates['errors'][domain.name] = 'Namecheap did not return an "OK" response.\nFull Response:\n{}'.format(req.text)
                    else:
                        logger.error('Namecheap API request returned status "%s"', req.status_code)
                        domain_updates[domain.id]['dns'] = 'no action'
                        domain_updates['errors'][domain.name] = {}
                        domain_updates['errors'][domain.name] = 'Namecheap did not return a 200 response.\nL.. API request returned status "{}"'.format(req.status_code)
                except Exception as error:
                    logger.error('Namecheap API request failed with error: %s', error)
                    domain_updates[domain.id]['dns'] = 'no action'
                    domain_updates['errors'][domain.name] = {}
                    domain_updates['errors'][domain.name] = 'Namecheap API request failed with error: {}'.format(error)
            else:
                domain_updates[domain.id]['dns'] = 'no action'
    logger.info('Domain release task completed at %s', datetime.datetime.now())
    return domain_updates


def release_servers(no_action=False):
    """Pull all servers currently checked-out in Shepherd and update the
    status to Available if the project's end date is today or in the past.

    Parameters:

    no_action       Defaults to False. Set to True to take no action and just
                    return a list of servers that should be released now.
    """
    servers_to_be_released = []
    # First get all server set to `Unavailable`
    queryset = StaticServer.objects.\
        filter(server_status__server_status='Unavailable')
    # Go through each `Unavailable` server and check it against projects
    for server in queryset:
        # Get all projects for the server
        try:
            project_queryset = ServerHistory.objects.\
                filter(server__ip_address=server.ip_address).latest('end_date')
        except ServerHistory.DoesNotExist:
            continue
        release_me = True
        # Check each project's end date to determine if all are in the past
        release_date = project_queryset.end_date
        warning_date = release_date - datetime.timedelta(1)
        # Check if date is before or is the end date
        if date.today() <= release_date:
            release_me = False
        # Check if tomorrow is the end date
        if date.today() == warning_date:
            release_me = False
            message = "Your server, {}, will be released tomorrow! " \
                        "Modify the project's end date as needed.".\
                        format(server.ip_address)
            if project_queryset.project.slack_channel:
                send_slack_msg(message, project_queryset.project.slack_channel)
            else:
                send_slack_msg(message)
        # If release_me is still true, release the server
        if release_me:
            servers_to_be_released.append(server)
            # Check no_action and just return list if it is set to True
            if no_action:
                return servers_to_be_released
            else:
                message = "Your server, {}, has been released.".\
                    format(server.ip_address)
                logger.info('Releasing %s back into the pool.', server.ip_address)
                if project_queryset.project.slack_channel:
                    send_slack_msg(message, project_queryset.project.slack_channel)
                else:
                    send_slack_msg(message)
                server.server_status = ServerStatus.objects.\
                    get(server_status='Available')
                server.save()
    return servers_to_be_released


def check_domains(domain=None):
    """Initiate a check of all domains in the Domain model and update each
    domain status.

    Parameters:

    domain          Defaults to None. Provide a domain name's primary key to
                    update only that domain. This arg is used when a user
                    requests a specific domain be updated via the web
                    interface.
    """
    # Get all domains from the database
    domain_list = []
    if domain:
        domain_queryset = Domain.objects.get(pk=domain)
        domain_list.append(domain_queryset)
    else:
        domain_queryset = Domain.objects.all()
        for result in domain_queryset:
            domain_list.append(result)
    domain_review = DomainReview(domain_list)
    lab_results = domain_review.check_domain_status()
    for domain in lab_results:
        try:
            # The `domain` is already a Domain object so this query might be
            # unnecessary :thinking_emoji:
            domain_instance = Domain.objects.get(name=domain.name)
            # Flip status if a domain has been flagged as burned
            if lab_results[domain]['burned']:
                logger.warning('Domain %s is burned', domain.name)
                domain_instance.health_status = HealthStatus.objects.\
                    get(health_status='Burned')
                domain_instance.domain_status = DomainStatus.objects.\
                    get(domain_status='Burned')
                message = '*{}* has been flagged as burned because: {}'.\
                    format(domain.name,
                           lab_results[domain]['burned_explanation'])
                if lab_results[domain]['categories']['bad']:
                    message = message + ' (Bad categories: {})'.\
                        format(lab_results[domain]['categories']['bad'])
                send_slack_msg(message)
            # Update other fields for the domain object
            domain_instance.health_dns = lab_results[domain]['health_dns']
            domain_instance.burned_explanation = \
                lab_results[domain]['burned_explanation']
            domain_instance.all_cat = \
                lab_results[domain]['categories']['all']
            domain_instance.talos_cat = \
                lab_results[domain]['categories']['talos']
            domain_instance.opendns_cat = \
                lab_results[domain]['categories']['opendns']
            domain_instance.bluecoat_cat = \
                lab_results[domain]['categories']['bluecoat']
            domain_instance.ibm_xforce_cat = \
                lab_results[domain]['categories']['xforce']
            domain_instance.trendmicro_cat = \
                lab_results[domain]['categories']['trendmicro']
            domain_instance.fortiguard_cat = \
                lab_results[domain]['categories']['fortiguard']
            domain_instance.mx_toolbox_status = \
                lab_results[domain]['categories']['mxtoolbox']
            domain_instance.save()
        except Exception as error:
            logger.error(
                'Error updating "%s" – %s', domain.name, error)
            pass


def update_dns(domain=None):
    """Initiate a check of all domains in the Domain model and update each
    domain's DNS records.

    Parameters:

    domain          Defaults to None. Provide a domain name's primary key to
                    update only that domain. This arg is used when a user
                    requests a specific domain be updated via the web
                    interface.
    """
    domain_list = []
    dns_toolkit = DNSCollector()
    # Get all domains from the database
    if domain:
        domain_queryset = Domain.objects.get(pk=domain)
        domain_list.append(domain_queryset)
        logger.info(
            'Starting DNS record update for an individual domain %s at %s', domain_queryset.name, datetime.datetime.now())
    else:
        logger.info(
            'Starting mass DNS record update at %s', datetime.datetime.now())
        domain_queryset = Domain.objects.all()
        for result in domain_queryset:
            domain_list.append(result)
    for domain in domain_list:
        # Get each type of DNS record for the domain
        try:
            try:
                temp = []
                ns_records_list = dns_toolkit.get_dns_record(domain.name, 'NS')
                for rdata in ns_records_list.response.answer:
                    for item in rdata.items:
                        temp.append(item.to_text())
                ns_records = ', '.join(x.strip('.') for x in temp)
            except Exception:
                ns_records = None
            try:
                temp = []
                a_records = dns_toolkit.get_dns_record(domain.name, 'A')
                for rdata in a_records.response.answer:
                    for item in rdata.items:
                        temp.append(item.to_text())
                a_records = ', '.join(temp)
            except Exception:
                a_records = None
            try:
                mx_records = dns_toolkit.return_dns_record_list(domain.name,
                                                                'MX')
            except Exception:
                mx_records = None
            try:
                txt_records = dns_toolkit.return_dns_record_list(domain.name,
                                                                 'TXT')
            except Exception:
                txt_records = None
            try:
                soa_records = dns_toolkit.return_dns_record_list(domain.name,
                                                                 'SOA')
            except Exception:
                soa_records = None
            try:
                dmarc_record = dns_toolkit.return_dns_record_list('_dmarc.' +
                                                                  domain.name,
                                                                  'TXT')
            except Exception:
                dmarc_record = None
            # Assemble the dict to be stored in the database
            dns_records_dict = {}
            if ns_records:
                dns_records_dict['ns'] = ns_records
            if a_records:
                dns_records_dict['a'] = a_records
            if mx_records:
                dns_records_dict['mx'] = mx_records
                if dmarc_record:
                    dns_records_dict['dmarc'] = dmarc_record
                else:
                    dns_records_dict['dmarc'] = 'No DMARC record!'
            if txt_records:
                dns_records_dict['txt'] = txt_records
            if soa_records:
                dns_records_dict['soa'] = soa_records
        except Exception as error:
            logger.error('Encountered an error processing records for %s - %s', domain, error)
            dns_records_dict = 'None'
        # Look-up the individual domain and save the new record string
        domain_instance = Domain.objects.get(name=domain.name)
        domain_instance.dns_record = dns_records_dict
        domain_instance.save()
    # Log task completed
    logger.info(
        'DNS update completed at %s', datetime.datetime.now())


def scan_servers(only_active=False):
    """Uses `python-nmap` to scan servers in the `StaticServer` model to
    report open ports.

    Parameters:

    only_active     Defaults to False. set to True to restrict
    """
    # Create the scanner
    scanner = nmap.PortScanner()
    # Get the servers stored as static/owned servers
    if only_active:
        server_queryset = StaticServer.objects.\
            filter(server_status__server_status='Active')
    else:
        server_queryset = StaticServer.objects.all()
    # Run a scan against each server in tbe queryset
    for server in server_queryset:
        scanner.scan(server.ip_address,
                     arguments='-sS -Pn -p- -R '
                               '--initial-rtt-timeout 100ms '
                               '--min-rtt-timeout 100ms '
                               '--max-rtt-timeout 200ms '
                               '--max-retries 1 '
                               '--max-scan-delay 0 --open')
        for host in scanner.all_hosts():
            for proto in scanner[host].all_protocols():
                lport = scanner[host][proto].keys()
                for port in lport:
                    if server.server_status.server_status == 'Unavailable':
                        message = 'Your server, {}, has an open port - {}'.\
                            format(host, port)
                        latest = ServerHistory.objects.filter(server=server)[0]
                        if latest.project.slack_channel:
                            send_slack_msg(message,
                                           latest.project.slack_channel)
                        else:
                            send_slack_msg(message)


def fetch_namecheap_domains():
    """Fetch a list of registered domains for the specified Namecheap account. A valid API key,
    username, and whitelisted IP address must be used. Returns a dictionary containing errors
    and each domain name paired with change status.
    
    Result statuses: created, updated, burned, updated & burned
    
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
    domain_changes['errors'] = {}
    domain_changes['updates'] = {}
    session = requests.Session()
    get_domain_list_endpoint = 'https://api.namecheap.com/xml.response?ApiUser={}&ApiKey={}&UserName={}&Command=namecheap.domains.getList&ClientIp={}&PageSize={}'

    logger.info(
        'Starting Namecheap synchronization task at %s', datetime.datetime.now())

    try:
        client_ip = settings.NAMECHEAP_CONFIG['client_ip']
        enable_namecheap = settings.NAMECHEAP_CONFIG['enable_namecheap']
        namecheap_api_key = settings.NAMECHEAP_CONFIG['namecheap_api_key']
        namecheap_username = settings.NAMECHEAP_CONFIG['namecheap_username']
        namecheap_page_size = settings.NAMECHEAP_CONFIG['namecheap_page_size']
        namecheap_api_username = settings.NAMECHEAP_CONFIG['namecheap_api_username']
    except KeyError as e:
        logger.error(
            'Encountered an error when fetching the Namecheap API configuration. Check your .django env file. Error: %s', e)
        return '[!] Encountered an error when fetching the Namecheap API configuration. Check your .django file. Error: {}'.format(e)

    try:
        # The Namecheap API call requires both usernames, a key, and a whitelisted IP
        req = session.get(
            get_domain_list_endpoint.format(
                namecheap_api_username, namecheap_api_key, namecheap_username,
                client_ip, namecheap_page_size))
        # Check if request returned a 200 OK
        if req.ok:
            # Convert Namecheap XML into an easy to use object for iteration
            root = objectify.fromstring(req.content)
            # Check the status to make sure it says "OK"
            namecheap_api_result = root.attrib['Status']
            if namecheap_api_result == 'OK':
                # Get all "Domain" node attributes from the XML response
                for domain in root.CommandResponse.DomainGetListResult.Domain:
                    domains_list.append(domain.attrib)
            elif namecheap_api_result == 'ERROR':
                error_message = 'Namecheap returned an "ERROR" response, so no domains were returned.'
                if 'Invalid request IP' in req.text:
                    error_message = '[!] ' + error_message + '\n' + 'L.. You are not connecting to Namecheap using your whitelisted IP address.'
                logger.error(
                    error_message + '\nFull Response:\n%s', req.text)
                return '[!] ' + error_message + '\nFull Response:\n{}'.format(req.text)
            else:
                logger.error(
                    'Namecheap did not return an "OK" response, so no domains were returned.\nFull Response:\n%s', req.text)
                return '[!] Namecheap did not return an "OK" response, so no domains were returned.\nFull Response:\n{}'.format(req.text)
        else:
            logger.error(
                'Namecheap API request failed. Namecheap did not return a 200 response.\nL.. API request returned status "%s"', req.status_code)
            return '[!] Namecheap API request failed. Namecheap did not return a 200 response.\nL.. API request returned status "{}"'.format(req.status_code)
    except Exception as error:
        logger.error(
            'Namecheap API request failed with error: %s', error)
        return '[!] Namecheap API request failed with error: {}'.format(error)
    # There's a chance no domains are returned if the provided usernames don't have any domains
    if domains_list:
        # Get the current list of Namecheap domains in the library
        domain_queryset = Domain.objects.filter(registrar='Namecheap')
        for domain in domain_queryset:
            # Check if a domain in the library is _not_ in the Namecheap response
            if not any(d['Name'] == domain.name for d in domains_list):
                # Domains not found in Namecheap have expired and fallen off the account
                if not domain.expired:
                    logger.info(
                        'Domain %s is not in the Namecheap data so it is now marked as expired', domain.name)
                    # Mark the domain as Expired
                    domain_changes['updates'][domain.id] = {}
                    domain_changes['updates'][domain.id]['domain'] = domain.name
                    domain_changes['updates'][domain.id]['change'] = 'expired'
                    entry = {}
                    domain.expired = True
                    domain.auto_renew = False
                    # If the domain expiration date is in the future, adjust it
                    if domain.expiration >= date.today():
                        domain.expiration = domain.expiration - datetime.timedelta(days=365)
                    try:
                        for attr, value in entry.items():
                            setattr(domain, attr, value)
                        domain.save()
                    except Exception as e:
                        pass
                    instance = DomainNote.objects.create(
                            domain=domain,
                            note='Automatically set to Expired because the domain did not appear in Namecheap during a sync.'
                        )
        # Now, loop over every domain returned by Namecheap
        for domain in domains_list:
            logger.info(
                'Domain {} is now being processed'.format(domain['Name']))
            # Prepare domain attributes for Domain model
            entry = {}
            entry['name'] = domain['Name']
            entry['registrar'] = 'Namecheap'
            # Set the WHOIS status based on WhoisGuard
            if domain['IsExpired'] == 'true':
                entry['expired'] = True
                # Expired domains have WhoisGuard set to `NOTPRESENT`
                entry['whois_status'] = WhoisStatus.objects.get(pk=2)
            else:
                try:
                    entry['whois_status'] = WhoisStatus.objects.get(
                        whois_status__iexact=domain['WhoisGuard'].capitalize())
                # Anything not `Enabled` or `Disabled`, set to `Unknown`
                except:
                    entry['whois_status'] = WhoisStatus.objects.get(pk=3)
            # Check if the domain is locked - locked generally means it's burned
            newly_burned = False
            if domain['IsLocked'] == 'true':
                logger.warning(
                    'Domain %s is marked as LOCKED by Namecheap', domain['Name'])
                domain_instance = Domain.objects.get(name=domain['Name'])
                health_burned = HealthStatus.objects.get(health_status='Burned')
                domain_burned = DomainStatus.objects.get(domain_status='Burned')
                # Even if already set to Burned, add some explanation if missing
                if not domain_instance.burned_explanation:
                    entry['burned_explanation'] = '<p>Namecheap has locked the domain. This is usually the result of a legal complaint related to phishing/malicious activities.</p>'
                # Update statuses if set to something else
                if not domain_instance.health_status == health_burned:
                    newly_burned = True
                    entry['health_status'] = health_burned
                if not domain_instance.domain_status == domain_burned:
                    newly_burned = True
                    entry['domain_status'] = domain_burned
            # Set AutoRenew status
            if domain['AutoRenew'] == 'false':
                entry['auto_renew'] = False
            # Convert Namecheap dates to Django
            entry['creation'] = datetime.datetime.strptime(
                domain['Created'], '%m/%d/%Y').strftime('%Y-%m-%d')
            entry['expiration'] = datetime.datetime.strptime(
                domain['Expires'], '%m/%d/%Y').strftime('%Y-%m-%d')
            try:
                # Update or create the domain record with assigned attrs
                instance, created = Domain.objects.update_or_create(
                    name=domain.get('Name'),
                    defaults=entry
                )
                for attr, value in entry.items():
                    setattr(instance, attr, value)
                logger.debug(
                    'Domain %s is being saved with this data: %s', domain['Name'], entry)
                instance.save()
                # Update the change tracking dict
                # Add entry to domain change tracking dict
                domain_changes['updates'][instance.id] = {}
                domain_changes['updates'][instance.id]['domain'] = domain['Name']
                if created and domain['IsLocked'] == 'true':
                    domain_changes['updates'][instance.id]['change'] = 'created & burned'
                elif created:
                    domain_changes['updates'][instance.id]['change'] = 'created'
                else:
                    if newly_burned:
                        domain_changes['updates'][instance.id]['change'] = 'burned'
                    else:
                        domain_changes['updates'][instance.id]['change'] = 'updated'
            except Exception as e:
                domain_changes['errors'][domain['Name']] = {}
                domain_changes['errors'][domain['Name']]['error'] = '{}'.format(e)
        logger.info(
            'Namecheap synchronization completed at %s with these changes:\n%s',
                datetime.datetime.now(),
                domain_changes)
        return domain_changes
    else:
        logger.warning(
            'No domains were returned for the provided Namecheap account!')
        return '[!] No domains were returned for the provided Namecheap account!'


def months_between(date1, date2):
    """Compare two dates and return the number of months beetween them."""
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


def json_datetime_converter(o):
    """Function to convert datetime objects to strings for json.dumps()."""
    if isinstance(o, datetime.datetime):
        return o.__str__()


def review_cloud_infrastructure():
    """Fetch active virtual machines/instances in Digital Ocean, Azure, and AWS and
    compare IP addresses to project infrastructure. Send a report to Slack if any
    instances are still alive after project end date or if an IP address is not found
    for a project.

    Returns a dictionary of cloud assets and encountered errors.
    """
    # Digital Ocean API endpoint for droplets
    DIGITAL_OCEAN_ENDPOINT = 'https://api.digitalocean.com/v2/droplets'
    # Fetch cloud API keys and tokens
    aws_key = settings.CLOUD_SERVICE_CONFIG['aws_key']
    aws_secret = settings.CLOUD_SERVICE_CONFIG['aws_secret']
    do_api_key = settings.CLOUD_SERVICE_CONFIG['do_api_key']

    # Fetch Slack configuration information
    slack_config = get_slack_config()
    if slack_config:
        slack_emoji = slack_config['slack_emoji']
        slack_username = slack_config['slack_username']
        slack_default_channel = slack_config['slack_channel']
        slack_webhook_url = slack_config['slack_webhook_url']
        slack_alert_target = slack_config['slack_alert_target']

    # Set timezone for dates to UTC
    utc = pytz.UTC
    # Create info dict
    vps_info = defaultdict()
    vps_info['errors'] = {}
    vps_info['instances'] = {}

    logger.info('Starting review of cloud infrastructure at %s', datetime.datetime.now())

    ###############
    # AWS Section #
    ###############

    # Create AWS client for EC2 using a default region and get a list of all regions
    aws_capable = True
    try:
        client = boto3.client('ec2', region_name='us-west-2', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    except ClientError as e:
        logger.error('AWS could not validate the provided credentials')
        aws_capable = False
        vps_info['errors']['aws'] = 'AWS could not validate the provided credentials.'
    if aws_capable:
        logger.info('AWS credentials are functional, beginning AWS review')
        # Loop over the regions to check each one for EC2 instances
        for region in regions:
            logger.info('Checking AWS region %s', region)
            # Create an EC2 resource for the region
            ec2 = boto3.resource('ec2', region_name=region, aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
            # Get all EC2 instances that are running
            running_instances = ec2.instances.filter(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
            # Loop over running instances to generate info dict
            for instance in running_instances:
                # Calculate how long the instance has been running in UTC
                time_up = months_between(instance.launch_time.replace(tzinfo=utc), datetime.datetime.today().replace(tzinfo=utc))
                tags = []
                name = 'Blank'
                if instance.tags:
                    for tag in instance.tags:
                        if 'name' in tag['Key']:
                            name = tag['Value']
                        elif 'Name' in tag['Key']:
                            name = tag['Value']
                        else:
                            tags.append('{}: {}'.format(tag['Key'], tag['Value']))
                pub_addresses = []
                pub_addresses.append(instance.private_ip_address)
                priv_addresses = []
                priv_addresses.append(instance.public_ip_address)
                # Add instance info to a dictionary
                vps_info['instances'][instance.id] = {
                  'id': instance.id,
                    'provider': 'Amazon Web Services {}'.format(region),
                    'name': name,
                    'type': instance.instance_type,
                    'monthly_cost': None,   # AWS cost is different and not easily calculated
                    'cost_to_date': None,   # AWS cost is different and not easily calculated
                    'state': instance.state['Name'],
                    'private_ip': priv_addresses,
                    'public_ip': pub_addresses,
                    'launch_time': instance.launch_time.replace(tzinfo=utc),
                    'time_up': '{} months'.format(time_up),
                    'tags': ', '.join(tags)
                }

    ###############
    # DO Section  #
    ###############

    # Get all Digital Ocean droplets for the account
    do_capable = True
    headers = {'Content-Type': 'application/json'}
    try:
        active_droplets = requests.get(DIGITAL_OCEAN_ENDPOINT, headers=headers, auth=BearerAuth(do_api_key)).json()
        logger.info('Digital Ocean credentials are functional, beginning droplet review')
    except:
        logger.error('Could not retrieve content from Digital Ocean with the provided API key')
        do_capable = False
        vps_info['errors']['digital_ocean'] = 'Could not retrieve content from Digital Ocean with the provided API key.'
    # Loop over the droplets to generate the info dict
    if do_capable:
        for droplet in active_droplets['droplets']:
            # Get the networking info
            if 'v4' in droplet['networks']:
                ipv4 = droplet['networks']['v4']
            else:
                ipv4 = []
            if 'v6' in droplet['networks']:
                ipv6 = droplet['networks']['v6']
            else:
                ipv6 = []
            # Create lists of public and private addresses
            pub_addresses = []
            priv_addresses = []
            for address in ipv4:
                if address['type'] == 'private':
                    priv_addresses.append(address['ip_address'])
                else:
                    pub_addresses.append(address['ip_address'])
            for address in ipv6:
                if address['type'] == 'private':
                    priv_addresses.append(address['ip_address'])
                else:
                    pub_addresses.append(address['ip_address'])
            # Calculate how long the instance has been running in UTC and cost to date
            time_up = months_between(
                datetime.datetime.strptime(droplet['created_at'].split('T')[0], '%Y-%m-%d').replace(tzinfo=utc),
                datetime.datetime.today().replace(tzinfo=utc)
                )
            cost_to_date = months_between(
                datetime.datetime.strptime(droplet['created_at'].split('T')[0], '%Y-%m-%d'),
                datetime.datetime.today()
                ) * droplet['size']['price_monthly']
            # Add an entry to the dict for the droplet
            vps_info['instances'][droplet['id']] = {
                'id': droplet['id'],
                'provider': 'Digital Ocean',
                'name': droplet['name'],
                'type': droplet['image']['distribution'] + " " + droplet['image']['name'],
                'monthly_cost': droplet['size']['price_monthly'],
                'cost_to_date': cost_to_date,
                'state': droplet['status'],
                'private_ip': priv_addresses,
                'public_ip': pub_addresses,
                'launch_time': datetime.datetime.strptime(droplet['created_at'].split('T')[0], '%Y-%m-%d').replace(tzinfo=utc),
                'time_up': '{} months'.format(time_up),
                'tags': ', '.join(droplet['tags'])
            }
    # Examine results to identify potentially unneeded/unused machines
    assets_in_use = []
    for instance_id, instance in vps_info['instances'].items():
        all_ip_addresses = []
        for address in instance['public_ip']:
            all_ip_addresses.append(address)
        for address in instance['private_ip']:
            all_ip_addresses.append(address)
        # Set instance's name to its ID if no name is set
        if instance['name']:
            instance_name = instance['name']
        else:
            instance_name = instance['id']
        # Check if any IP address is associated with a project
        queryset = TransientServer.objects.select_related('project').filter(ip_address__in=all_ip_addresses)
        if queryset:
            for result in queryset:
                if result.project.end_date < instance['launch_time'].date():
                    if slack_config:
                        if result.project.slack_channel:
                            slack_data = craft_cloud_message(
                                slack_username, slack_emoji, slack_default_channel,
                                instance['launch_time'], result.project, result.project.end_date,
                                instance['provider'], instance_name, instance['tags'])
                            # send_slack_msg(message, slack_channel=result.project.slack_channel)
                            response = requests.post(slack_webhook_url,
                                 data=slack_data,
                                 headers={'Content-Type':
                                          'application/json'})
                        else:
                            slack_data = craft_cloud_message(
                                slack_username, slack_emoji, slack_default_channel,
                                instance['launch_time'], result.project, result.project.end_date,
                                instance['provider'], instance_name, instance['tags'])
                            response = requests.post(slack_webhook_url,
                                 data=slack_data,
                                 headers={'Content-Type':
                                          'application/json'})
                else:
                    # Project is still active, so track these assets for later
                    assets_in_use.append(instance_id)
        else:
            if 'gw_ignore' in instance['tags']:
                assets_in_use.append(instance_id)
            else:
                if slack_config:
                    slack_data = craft_unknown_asset_message(
                        slack_username, slack_emoji, slack_default_channel,
                        instance['launch_time'], instance['provider'],
                        instance_name, instance['tags'])
                    response = requests.post(slack_webhook_url,
                            data=slack_data,
                            headers={'Content-Type':
                                    'application/json'})
    # Drop active assets from the dict
    for instance_id in assets_in_use:
        del vps_info[instance_id]
    # Return the stale cloud asset data in JSON for the task results
    json_data = json.dumps(dict(vps_info), default=json_datetime_converter, indent=2)
    logger.info('Cloud review completed at %s', datetime.datetime.now())
    logger.info('JSON results:\n%s', json_data)
    return json_data


def check_expiration():
    """Fetch all domains from the library and check the expiration dates. If
    the expiration date is less than or equal to the current date, check the
    auto-renew status. Then either expire the domain or add one year to the
    expiration date.
    """
    domain_queryset = Domain.objects.all()
    for domain in domain_queryset:
        if domain.expiration <= date.today():
            if domain.auto_renew:
                logger.info(
                    'Adding one year to %s\'s expiration date', domain.name)
                domain.expiration = domain.expiration + datetime.timedelta(days=365)
                domain.expired = False
                domain.save()
            else:
                logger.info(
                    'Expiring domain %s due to expiration date, %s',
                    domain.name,
                    domain.expiration)
                domain.expired = True
                domain.save()
