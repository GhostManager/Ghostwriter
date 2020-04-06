"""This contains tasks to be run using Django Q and Redis."""

# Import the shepherd application's models and settings
from django.db.models import Q
from django.conf import settings
from django.core.files import File

from .models import (Domain, History, DomainStatus, HealthStatus,
    StaticServer, ServerStatus, ServerHistory, WhoisStatus, TransientServer)

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
                print('[!] Request to Slack returned an error %s, the '
                      'response is:\n%s' % (response.status_code,
                                            response.text))


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


def release_domains(no_action=False):
    """Pull all domains currently checked-out in Shepherd and update the
    status to Available if the project's end date is today or in the past.

    Parameters:

    no_action       Defaults to False. Set to True to take no action and just
                    return a list of domains that should be released now.
    """
    domains_to_be_released = []
    # First get all domains set to `Unavailable`
    queryset = Domain.objects.\
        filter(domain_status__domain_status='Unavailable')
    # Go through each `Unavailable` domain and check it against projects
    for domain in queryset:
        # Get all projects for the domain
        try:
            project_queryset = History.objects.filter(domain__name=domain.name).latest('end_date')
        except History.DoesNotExist:
            continue
        release_me = True
        release_date = project_queryset.end_date
        warning_date = release_date - datetime.timedelta(1)
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
        # If release_me is still true, release the domain
        if release_me:
            domains_to_be_released.append(domain)
            # Check no_action and just return list if it is set to True
            if no_action:
                return domains_to_be_released
            else:
                message = 'Your domain, {}, has been released.'.format(domain.name)
                print('Releasing {} back into the pool.'.format(domain.name))
                if project_queryset.project.slack_channel:
                    send_slack_msg(message, project_queryset.project.slack_channel)
                else:
                    send_slack_msg(message)
                domain.domain_status = DomainStatus.objects.\
                    get(domain_status='Available')
                domain.save()
    return domains_to_be_released


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
                print('Releasing {} back into the pool.'.format(server.ip_address))
                if project_queryset.project.slack_channel:
                    # send_slack_msg(message, project_queryset.project.slack_channel)
                    print(message, project_queryset.project.slack_channel)
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
            print('[!] Error updating "{}". Error: {}'.format(domain.name,
                                                              error))
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
    else:
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
                ns_records = 'None'
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
            # Assemble the string to be stored in the database
            dns_records_string = ''
            if ns_records:
                dns_records_string += 'NS: %s ::: ' % ns_records
            if a_records:
                dns_records_string += 'A: %s ::: ' % a_records
            if mx_records:
                dns_records_string += 'MX: %s ::: ' % mx_records
                if dmarc_record:
                    dns_records_string += 'DMARC: %s ::: ' % dmarc_record
                else:
                    dns_records_string += 'DMARC: No DMARC record! ::: '
            if txt_records:
                dns_records_string += 'TXT: %s ::: ' % txt_records
            if soa_records:
                dns_records_string += 'SOA: %s ::: ' % soa_records
        except Exception:
            dns_records_string = 'None'
        # Look-up the individual domain and save the new record string
        domain_instance = Domain.objects.get(name=domain.name)
        domain_instance.dns_record = dns_records_string
        domain_instance.save()


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
    username, and whitelisted IP address must be used. The returned XML contains entries for
    domains like this:
    
    <RequestedCommand>namecheap.domains.getList</RequestedCommand>
    <CommandResponse Type="namecheap.domains.getList">
        <DomainGetListResult>
            <Domain ID="127"
            Name="domain1.com"
            User="owner"
            Created="02/15/2016"
            Expires="02/15/2022"
            IsExpired='False'
            IsLocked='False'
            AutoRenew='False'
            WhoisGuard="ENABLED"
            IsPremium="true"
            IsOurDNS="true"/>
        </DomainGetListResult>
    """
    domains_list = []
    session = requests.Session()
    get_domain_list_endpoint = 'https://api.namecheap.com/xml.response?ApiUser={}&ApiKey={}&UserName={}&Command=namecheap.domains.getList&ClientIp={}&PageSize={}'

    client_ip = settings.NAMECHEAP_CONFIG['client_ip']
    enable_namecheap = settings.NAMECHEAP_CONFIG['enable_namecheap']
    namecheap_api_key = settings.NAMECHEAP_CONFIG['namecheap_api_key']
    namecheap_username = settings.NAMECHEAP_CONFIG['namecheap_username']
    namecheap_page_size = settings.NAMECHEAP_CONFIG['namecheap_page_size']
    namecheap_api_username = settings.NAMECHEAP_CONFIG['namecheap_api_username']

    try:
        # The Namecheap API call requires both usernames, a key, and a whitelisted IP
        req = session.get(
            get_domain_list_endpoint.format(
                namecheap_api_username, namecheap_api_key, namecheap_username,
                client_ip,namecheap_page_size))
        # Check if request returned a 200 OK
        if req.ok:
            # Convert Namecheap XML into an easy to use object for iteration
            root = objectify.fromstring(req.content)
            # Check the status to make sure it says "OK"
            namecheap_api_result = root.attrib['Status']
            if namecheap_api_result == 'OK':
                # Get all "Domain" node attributes from the XML response
                print('[+] Namecheap returned status "{}"'.format(namecheap_api_result))
                for domain in root.CommandResponse.DomainGetListResult.Domain:
                    domains_list.append(domain.attrib)
            elif namecheap_api_result == 'ERROR':
                print('[!] Namecheap returned an "ERROR" response, so no domains were returned.')
                if 'Invalid request IP' in req.text:
                    print('L.. You are not connecting to Namecheap using your whitelisted IP address.')
                print('Full Response:\n{}'.format(req.text))
            else:
                print('[!] Namecheap did not return an "OK" response, so no domains were returned.')
                print('Full Response:\n{}'.format(req.text))
        else:
            print('[!] Namecheap API request failed. Namecheap did not return a 200 response.')
            print('L.. API request returned status "{}"'.format(req.status_code))
    except Exception as error:
        print('[!] Namecheap API request failed with error: {}'.format(error))
    # There's a chance no domains are returned if the provided usernames don't have any domains
    if domains_list:
        for domain in domains_list:
            entry = {}
            entry['registrar'] = 'Namecheap'
            # Set the WHOIS status based on WhoisGuard
            if domain['IsExpired'] == 'true':
                entry['expired'] = True
                entry['whois_status'] = WhoisStatus.objects.get(pk=2)
            else:
                try:
                    entry['whois_status'] = WhoisStatus.objects.get(
                        whois_status__iexact=domain['WhoisGuard'].capitalize())
                # Anytying no `Enabled` or `Disabled`, set to `Unknown`
                except:
                    entry['whois_status'] = WhoisStatus.objects.get(pk=3)
            # Set AutoRenew status
            if domain['AutoRenew'] == 'false':
                entry['auto_renew'] = False
            # Convert Namecheap dates to Django
            entry['creation'] = datetime.datetime.strptime(
                domain['Created'], "%m/%d/%Y").strftime("%Y-%m-%d")
            entry['expiration'] = datetime.datetime.strptime(
                domain['Expires'], "%m/%d/%Y").strftime("%Y-%m-%d")
            try:
                instance, created = Domain.objects.update_or_create(
                    name=domain.get('Name')
                )
                for attr, value in entry.items():
                    setattr(instance, attr, value)
                instance.save()
            except Exception as e:
                pass
    else:
        print('[!] No domains were returned for the provided account!')


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


def review_cloud_infrastructure():
    """Fetch active virtual machines/instances in Digital Ocean, Azure, and AWS and
    compare IP addresses to project infrastructure. Send a report to Slack if any
    instances are still alive after project end date or if an IP address is not found
    for a project.
    """
    DIGITAL_OCEAN_ENDPOINT = 'https://api.digitalocean.com/v2/droplets'

    aws_key = settings.CLOUD_SERVICE_CONFIG['aws_key']
    aws_secret = settings.CLOUD_SERVICE_CONFIG['aws_secret']
    do_api_key = settings.CLOUD_SERVICE_CONFIG['do_api_key']

    # Set timezone for dates to UTC
    utc = pytz.UTC
    # Create info dict
    vps_info = defaultdict()
    # Create AWS client for EC2 using a default region and get a list of all regions
    aws_capable = True
    try:
        client = boto3.client('ec2', region_name='us-west-2', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    except ClientError as e:
        aws_capable = False
        print('[!] AWS could not validate the provided credentials.')
    if aws_capable:
        # Loop over the regions to check each one for EC2 instances
        for region in regions:
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
                if instance.tags:
                    for tag in instance.tags:
                        if 'Name' in tag['Key']:
                            name = tag['Value']
                        else:
                            tags.append(tag)
                else:
                    name = "Blank"
                pub_addresses = []
                pub_addresses.append(instance.private_ip_address)
                priv_addresses = []
                priv_addresses.append(instance.public_ip_address)
                # Add instance info to a dictionary         
                vps_info[instance.id] = {
                    'Provider': 'Amazon Web Services',
                    'Name': name,
                    'Type': instance.instance_type,
                    'Monthly Cost': None,   # AWS cost is different and not easily calculated
                    'Cost to Date': None,   # AWS cost is different and not easily calculated
                    'State': instance.state['Name'],
                    'Private IP': priv_addresses,
                    'Public IP': pub_addresses,
                    'Launch Time': instance.launch_time.replace(tzinfo=utc),
                    'Time Up': '{} months'.format(time_up),
                    'Tags': tags
                }

    # Get all Digital Ocean droplets for the account
    do_capable = True
    try:
        active_droplets = requests.get(DIGITAL_OCEAN_ENDPOINT, auth=BearerAuth(do_api_key)).json()
    except:
        do_capable = False
        print('[!] Could not retrieve content from Digital Ocean with the provided API key.')
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
            # Add an entry to th dict for the droplet
            vps_info[droplet['id']] = {
                'Provider': 'Digital Ocean',
                'Name': droplet['name'],
                'Type': droplet['image']['distribution'] + " " + droplet['image']['name'],
                'Monthly Cost': droplet['size']['price_monthly'],
                'Cost to Date': cost_to_date,
                'State': droplet['status'],
                'Private IP': priv_addresses,
                'Public IP': pub_addresses,
                'Launch Time': datetime.datetime.strptime(droplet['created_at'].split('T')[0], '%Y-%m-%d').replace(tzinfo=utc),
                'Time Up': '{} months'.format(time_up),
                'Tags': ', '.join(droplet['tags'])
            }
    # Examine results to identify potentially unneeded/unused machines
    for instance_id, instance in vps_info.items():
        all_ip_addresses = []
        for address in instance['Public IP']:
            all_ip_addresses.append(address)
        for address in instance['Private IP']:
            all_ip_addresses.append(address)
        queryset = TransientServer.objects.select_related('project').filter(ip_address__in=all_ip_addresses)
        if queryset:
            for result in queryset:
                if result.project.end_date < instance['Launch Time'].date():
                    message = 'Assessment ended on {} and this server on {} is still running:\n\n {} ({}) Tags: {}'.format(
                        result.project.end_date, instance['Provider'], instance['Name'],
                        ', '.join(instance['Public IP']), instance['Tags'])
                    if result.project.slack_channel:
                        send_slack_msg(message, slack_channel=result.project.slack_channel)
                    else:
                        send_slack_msg(message)
                else:
                    print('[+] Server is still being used: {}'.format(instance))
        else:
            print('[+] Server not found in Ghostwriter: {}'.format(instance))


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
                print('Adding one year to {}\'s expiration date.'.format(domain.name))
                domain.expiration = domain.expiration + datetime.timedelta(days=365)
                domain.expired = False
                domain.save()
            else:
                print('Expiring domain {} due to expiration date, {}.'.format(domain.name, domain.expiration))
                domain.expired = True
                domain.save()
