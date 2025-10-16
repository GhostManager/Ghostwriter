"""This contains tasks to be run using Django Q and Redis."""

# Standard Libraries
import json
import logging.config
import traceback
from asgiref.sync import async_to_sync
from collections import defaultdict
from datetime import date, datetime, timedelta
from math import ceil

# Django Imports
from django.db.models import Q

# 3rd Party Libraries
import nmap
import requests
from botocore.exceptions import ClientError
from channels.layers import get_channel_layer
from lxml import objectify

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import (
    CloudServicesConfiguration,
    NamecheapConfiguration,
    VirusTotalConfiguration,
)
from ghostwriter.modules.cloud_monitors import (
    fetch_aws_ec2,
    fetch_aws_lightsail,
    fetch_aws_s3,
    fetch_digital_ocean,
    test_aws,
)
from ghostwriter.modules.dns_toolkit import DNSCollector
from ghostwriter.modules.notifications_slack import SlackNotification
from ghostwriter.modules.review import DomainReview
from ghostwriter.shepherd.models import (
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


def namecheap_reset_dns(namecheap_config, domain):
    """
    Try to use the Namecheap API to reset the DNS records for a target domain.

    **Parameters**

    ``domain``
        Domain to reset that is registered with Namecheap
    """
    results = {"result": "reset", "error": ""}

    # Configure Namecheap API requests
    session = requests.Session()
    reset_records_endpoint = "https://api.namecheap.com/xml.response?apiuser={}&apikey={}&username={}&Command=namecheap.domains.dns.setHosts&ClientIp={}&SLD={}&TLD={}"
    reset_record_template = "&HostName1=@&RecordType1=URL&Address1=http://www.namecheap.com&TTL1=100"

    logger.info("Attempting to reset DNS on Namecheap for %s", domain.name)
    try:
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
            # Convert Namecheap XML into an easy-to-use object for iteration
            root = objectify.fromstring(req.content)
            # Check the status to make sure it says "OK"
            namecheap_api_result = root.attrib["Status"]
            if namecheap_api_result == "OK":
                is_success = root.CommandResponse.DomainDNSSetHostsResult.attrib["IsSuccess"]
                # warnings = root.CommandResponse.DomainDNSSetHostsResult.Warnings
                if is_success == "true":
                    logger.info("Successfully reset DNS records for %s", domain.name)
                    results["result"] = "reset"
                else:
                    logger.warning(
                        'Namecheap did not return True for "IsSuccess" when resetting DNS records for %s',
                        domain.name,
                    )
                    results["result"] = "reset failed"
            elif namecheap_api_result == "ERROR":
                error_num = root.Errors.Error.attrib["Number"]
                error = root.Errors.Error.text
                logger.error("DNS Error %s: %s", error_num, error)
                results["result"] = "no action"
                results["error"] = "DNS Error {}: {}".format(error_num, error)
            else:
                logger.error(
                    'Namecheap did not return an "OK" response – %s',
                    req.text,
                )
                results["result"] = "no action"
                results["error"] = 'Namecheap did not return an "OK" response.\nFull Response:\n{}'.format(req.text)
        else:
            logger.error(
                'Namecheap API request returned status "%s"',
                req.status_code,
            )
            results["result"] = "no action"
            results["error"] = 'Namecheap did not return a 200 response.\nL.. API request returned status "{}"'.format(
                req.status_code
            )
    except Exception as error:
        logger.error("Namecheap API request failed with error: %s", error)
        results["result"] = "no action"
        results["error"] = "Namecheap API request failed with error: {}".format(error)

    return results


def release_domains(no_action=False):
    """
    Pull all :model:`shepherd.Domain` entries currently checked-out and update the
    status to ``Available`` if the related :model:`rolodex.Project` entry's ``end_date``
    value is today or in the past.

    **Parameters**

    ``no_action``
        Set to True to take no action and just return a list of domains that should
        be released (Default: False)
    """
    domain_updates = {"errors": {}}

    slack = SlackNotification()
    namecheap_config = NamecheapConfiguration.get_solo()

    # Start tracking domain releases
    domains_to_be_released = []

    # First, get all domains set to ``Unavailable``
    queryset = Domain.objects.filter(domain_status__domain_status="Unavailable")

    # Go through each ``Unavailable`` domain and check it against projects
    logger.info("Starting domain release task at %s", datetime.now())
    for domain in queryset:
        release_me = True
        slack_channel = None
        try:
            # Get latest project checkout for domain
            project_queryset = History.objects.filter(domain__name=domain.name).latest("end_date")
            release_date = project_queryset.end_date
            warning_date = release_date - timedelta(1)
            if project_queryset.project.slack_channel:
                slack_channel = project_queryset.project.slack_channel
            # Check if date is before or is the end date
            if date.today() <= release_date:
                release_me = False
            # Check if tomorrow is the end date
            if date.today() == warning_date:
                release_me = False
                message = "Reminder: your project is ending soon and your domain, {}, will be released when it does. If your project is still ending after EOB on {}, you don't need to do anything!".format(
                    domain.name,
                    release_date,
                )
                if slack.enabled:
                    err = slack.send_msg(message, slack_channel)
                    if err:
                        logger.warning(
                            "Attempt to send a Slack notification returned an error: %s",
                            err,
                        )
        except History.DoesNotExist:
            logger.warning("The domain %s has no project history, so releasing it", domain.name)
            release_date = datetime.today()

        # If ``release_me`` is still ``True``, release the domain
        if release_me:
            logger.warning("The domain %s is marked for release", domain.name)
            domains_to_be_released.append(domain)
            domain_updates[domain.id] = {}
            domain_updates[domain.id]["domain"] = domain.name
            domain_updates[domain.id]["release_date"] = release_date

            # Check no_action and just return list if it is set to True
            if no_action:
                logger.info(
                    "Would have released %s back into the pool, but task was set to take no action.",
                    domain.name,
                )
                domain_updates[domain.id]["change"] = "no action"
            else:
                logger.info("Releasing %s back into the pool.", domain.name)
                message = "Your domain, {}, has been released.".format(domain.name)
                if slack.enabled:
                    err = slack.send_msg(message, slack_channel)
                    if err:
                        logger.warning(
                            "Attempt to send a Slack notification returned an error: %s",
                            err,
                        )
                domain.domain_status = DomainStatus.objects.get(domain_status="Available")
                domain.save()
                domain_updates[domain.id]["change"] = "released"

            # Handle DNS record resets
            if domain.reset_dns and domain.registrar:
                if namecheap_config.enable and domain.registrar.lower() == "namecheap":
                    reset_result = namecheap_reset_dns(namecheap_config, domain)
                    domain_updates[domain.id]["dns"] = reset_result["result"]
                    if reset_result["error"]:
                        domain_updates["errors"][domain.name] = {}
                        domain_updates["errors"][domain.name] = reset_result["error"]
            else:
                domain_updates[domain.id]["dns"] = "no action"

    logger.info("Domain release task completed at %s", datetime.now())
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
    server_updates = {"errors": {}}
    servers_to_be_released = []

    slack = SlackNotification()

    # First get all server set to ``Unavailable``
    queryset = StaticServer.objects.filter(server_status__server_status="Unavailable")

    # Go through each ``Unavailable`` server and check it against projects
    for server in queryset:
        release_me = True
        slack_channel = None

        # Get the latest project checkout for the server
        try:
            project_queryset = ServerHistory.objects.filter(server__ip_address=server.ip_address).latest("end_date")
            release_date = project_queryset.end_date
            warning_date = release_date - timedelta(1)
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
                if slack.enabled:
                    err = slack.send_msg(message, slack_channel)
                    if err:
                        logger.warning(
                            "Attempt to send a Slack notification returned an error: %s",
                            err,
                        )
        except ServerHistory.DoesNotExist:
            logger.warning(
                "The server %s has no project history, so releasing it",
                server.ip_address,
            )
            release_date = datetime.today()

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
                if slack.enabled:
                    err = slack.send_msg(message, slack_channel)
                    if err:
                        logger.warning(
                            "Attempt to send a Slack notification returned an error: %s",
                            err,
                        )
                server.server_status = ServerStatus.objects.get(server_status="Available")
                server.save()
                server_updates[server.id]["change"] = "released"

    logger.info("Server release task completed at %s", datetime.now())
    return server_updates


def check_domains(domain_id=None):
    """
    Initiate a check of all :model:`shepherd.Domain` and update the ``domain_status`` values.

    **Parameters**

    ``domain_id``
        Individual domain's primary key to update only that domain (Default: None)
    """
    domain_updates = {"errors": {}}

    # Fetch Slack configuration information
    slack = SlackNotification()

    # Get target domain(s) from the database or the target ``domain``
    domain_list = []
    sleep_time_override = None
    if domain_id:
        try:
            domain_queryset = Domain.objects.get(pk=domain_id)
            domain_list.append(domain_queryset)
            logger.info("Checking only one domain, so disabling sleep time for VirusTotal")
            sleep_time_override = 0
        except Domain.DoesNotExist:
            domain_updates[domain_id] = {}
            domain_updates[domain_id]["change"] = "error"
            domain_updates["errors"][domain_id] = {}
            domain_updates["errors"][domain_id] = f"Requested domain ID, {domain_id}, does not exist"
            logger.exception("Requested domain ID, %s, does not exist", domain_id)
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
    domain_review = DomainReview(domain_queryset=domain_list, sleep_time_override=sleep_time_override)
    lab_results = domain_review.check_domain_status()

    # Update the domains as needed
    for k, v in lab_results.items():
        domain_qs = v["domain_qs"]
        change = "no action"
        domain_updates[k] = {}
        domain_updates[k]["domain"] = v["domain"]
        if "vt_results" in lab_results[k]:
            domain_updates[k]["vt_results"] = lab_results[k]["vt_results"]
        try:
            # Flip status if a domain has been flagged as burned
            if lab_results[k]["burned"]:
                domain_qs.health_status = HealthStatus.objects.get(health_status="Burned")
                change = "burned"
                pretty_categories = []
                for vendor, category in lab_results[k]["categories"].items():
                    pretty_categories.append(f"{vendor}: {category}")

                scanners = "N/A"
                if lab_results[k]["scanners"]:
                    scanners = "\n".join(lab_results[k]["scanners"])

                if slack.enabled:
                    blocks = slack.craft_burned_msg(
                        v["domain"],
                        "\n".join(pretty_categories),
                        scanners,
                        lab_results[k]["burned_explanation"],
                    )
                    if slack.enabled:
                        err = slack.send_msg(
                            message=f"Domain burned: {v['domain']}",
                            blocks=blocks,
                        )
                        if err:
                            logger.warning(
                                "Attempt to send a Slack notification returned an error: %s",
                                err,
                            )

                    # Check if the domain is checked-out and send a message to that project channel
                    try:
                        latest_checkout = History.objects.filter(domain=domain_qs).latest("end_date")
                        if (
                            latest_checkout.end_date >= date.today()
                            and latest_checkout.project.slack_channel
                            and slack.enabled
                        ):
                            err = slack.send_msg(
                                message=f"Domain burned: {v['domain']}",
                                channel=latest_checkout.project.slack_channel,
                                blocks=blocks,
                            )
                            if err:
                                logger.warning(
                                    "Attempt to send a Slack notification returned an error: %s",
                                    err,
                                )
                    except History.DoesNotExist:
                        pass
            # If the domain isn't marked as burned, check for any informational warnings
            else:
                if lab_results[k]["warnings"]["total"] > 0:
                    logger.info("Domain is not burned but there are warnings, so preparing notification")
                    blocks = slack.craft_warning_msg(
                        v["domain"],
                        "VirusTotal Submission",
                        lab_results[k]["warnings"]["messages"],
                    )
                    if slack.enabled:
                        err = slack.send_msg(
                            message=f"Domain event warning for {v['domain']}",
                            blocks=blocks,
                        )
                        if err:
                            logger.warning(
                                "Attempt to send a Slack notification returned an error: %s",
                                err,
                            )
            # Update other fields for the domain object
            if lab_results[k]["burned"] and "burned_explanation" in lab_results[k]:
                if lab_results[k]["burned_explanation"]:
                    domain_qs.burned_explanation = "\n".join(lab_results[k]["burned_explanation"])
            if lab_results[k]["categories"] != domain_qs.categorization:
                change = "categories updated"
            if lab_results[k]["categories"]:
                # Save the JSON data to the JSONField with no alteration (e.g., ``json.dumps()``)
                domain_qs.categorization = lab_results[k]["categories"]
            else:
                domain_qs.categorization = {"VirusTotal": "Uncategorized"}
            domain_qs.last_health_check = datetime.now()
            domain_qs.save()
            domain_updates[k]["change"] = change
        except Exception:
            trace = traceback.format_exc()
            domain_updates[k]["change"] = "error"
            domain_updates["errors"][v["domain"]] = {}
            domain_updates["errors"][v["domain"]] = trace
            logger.exception('Error updating "%s"', v["domain"])

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

    domain_updates = {"errors": {}}

    # Get the target domain(s) from the database
    if domain:
        domain_queryset = Domain.objects.get(pk=domain)
        domain_list.append(domain_queryset)
        logger.info(
            "Starting DNS record update for an individual domain %s at %s",
            domain_queryset.name,
            datetime.now(),
        )
    else:
        logger.info("Starting mass DNS record update at %s", datetime.now())
        domain_queryset = Domain.objects.filter(~Q(domain_status=DomainStatus.objects.get(domain_status="Expired")))
        for result in domain_queryset:
            domain_list.append(result)

    record_types = ["A", "NS", "MX", "TXT", "CNAME", "SOA", "DMARC"]
    dns_records = dns_toolkit.run_async_dns(domains=domain_list, record_types=record_types)

    for d in domain_list:
        domain_updates[d.id] = {}
        domain_updates[d.id]["domain"] = d.name

        if d.name in dns_records:
            try:
                a_record = dns_records[d.name]["a_record"]
                mx_record = dns_records[d.name]["mx_record"]
                ns_record = dns_records[d.name]["ns_record"]
                txt_record = dns_records[d.name]["txt_record"]
                soa_record = dns_records[d.name]["soa_record"]
                cname_record = dns_records[d.name]["cname_record"]
                dmarc_record = dns_records[d.name]["dmarc_record"]

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
                dns_records_dict = {
                    "ns": ns_record,
                    "a": a_record,
                    "mx": mx_record,
                    "cname": cname_record,
                    "dmarc": dmarc_record,
                    "txt": txt_record,
                    "soa": soa_record,
                }

                # Look-up the individual domain and save the new record string
                domain_instance = Domain.objects.get(name=d.name)
                domain_instance.dns = dns_records_dict
                domain_instance.save()
                domain_updates[d.id]["result"] = "updated"
            except Exception:
                trace = traceback.format_exc()
                logger.exception("Failed updating DNS records for %s", d.name)
                domain_updates["errors"][d.name] = "Failed updating DNS records: {traceback}".format(traceback=trace)
        else:
            logger.warning("The domain %s was not found in the returned DNS records", d.name)
            domain_updates[d.id]["result"] = "no results"

    # Log task completed
    logger.info("DNS update completed at %s", datetime.now())
    return domain_updates


def scan_servers(only_active=False):
    """
    Uses ``python-nmap`` to scan individual :model:`shepherd.StaticServer`
    and :model:`shepherd.TransientServer` to identify open ports.

    **Parameters**

    ``only_active``
        Only scan servers marked as in-use (Default: False)
    """
    slack = SlackNotification()

    # Create the scanner
    scanner = nmap.PortScanner()
    # Get the servers stored as static/owned servers
    if only_active:
        server_queryset = StaticServer.objects.filter(server_status__server_status="Active")
    else:
        server_queryset = StaticServer.objects.all()
    # Run a scan against each server in the queryset
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
                        message = "Your server, {}, has an open port - {}".format(host, port)
                        latest = ServerHistory.objects.filter(server=server)[0]
                        if slack.enabled:
                            if latest.project.slack_channel:
                                err = slack.send_msg(message, latest.project.slack_channel)
                            else:
                                err = slack.send_msg(message)
                            if err:
                                logger.warning(
                                    "Attempt to send a Slack notification returned an error: %s",
                                    err,
                                )


def fetch_namecheap_domains():
    """
    Fetch a list of registered domains for the specified Namecheap account. A valid API key,
    username, and whitelisted IP address must be used. Returns a dictionary containing errors
    and each domain name paired with change status.

    Result status: created, updated, burned, updated & burned

    The returned XML contains entries for domains, errors, warnings, and paging with this structure:

    <ApiResponse Status="OK" xmlns="http://api.namecheap.com/xml.response">
        <Errors />
        <Warnings />
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
            <Paging>
                <TotalItems>1</TotalItems>
                <CurrentPage>1</CurrentPage>
                <PageSize>20</PageSize>
            </Paging>
        </CommandResponse>
    </ApiResponse>
    """
    domains_list = []
    domain_changes = {"errors": {}, "updates": {}}

    # Always begin assuming one page of results
    pages = 1
    session = requests.Session()
    get_domain_list_endpoint = "https://api.namecheap.com/xml.response?ApiUser={}&ApiKey={}&UserName={}&Command=namecheap.domains.getList&ClientIp={}&PageSize={}&Page={}"

    logger.info("Starting Namecheap synchronization task at %s", datetime.now())

    namecheap_config = NamecheapConfiguration.get_solo()

    # Keep fetching domains until we reach the end of the pages
    i = 1
    while i <= pages:
        try:
            logger.info("Requesting page %s of %s", i, pages)
            # The Namecheap API call requires both usernames, a key, and a whitelisted IP
            req = session.get(
                get_domain_list_endpoint.format(
                    namecheap_config.api_username,
                    namecheap_config.api_key,
                    namecheap_config.username,
                    namecheap_config.client_ip,
                    namecheap_config.page_size,
                    i,
                )
            )
            # Check if request returned a 200 OK
            if req.ok:
                # Convert Namecheap XML into an easy-to-use object for iteration
                root = objectify.fromstring(req.content)
                # Check the status to make sure it says "OK"
                namecheap_api_result = root.attrib["Status"]
                if namecheap_api_result == "OK":
                    # Check paging info
                    total_domains = root.CommandResponse.Paging.TotalItems
                    page_size = root.CommandResponse.Paging.PageSize

                    # Divide total by page size and round up for total pages
                    total_pages = ceil(total_domains / page_size)
                    if total_pages != pages:
                        logger.info("Updating page total to %s", total_pages)
                        pages = total_pages

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
                        'Namecheap did not return an "OK" or "ERROR" response: %s',
                        req.text,
                    )
                    domain_changes["errors"][
                        "namecheap"
                    ] = 'Namecheap did not return an "OK" or "ERROR" response: {response}'.format(response=req.text)
                    return domain_changes
            else:
                logger.error("Namecheap returned a %s response: %s", req.status_code, req.text)
                domain_changes["errors"]["namecheap"] = "Namecheap returned a {status_code} response: {text}".format(
                    status_code=req.status_code, text=req.text
                )
                return domain_changes
        except Exception:
            trace = traceback.format_exc()
            logger.exception("Namecheap API request failed")
            domain_changes["errors"]["namecheap"] = "The Namecheap API request failed: {traceback}".format(
                traceback=trace
            )
            return domain_changes

        # Increment page counter
        i += 1

    # No domains are returned if the provided account doesn't have any domains
    if domains_list:
        # Get the current list of Namecheap domains in the library
        domain_queryset = Domain.objects.filter(registrar="Namecheap")
        expired_status = DomainStatus.objects.get(domain_status="Expired")
        burned_status = DomainStatus.objects.get(domain_status="Burned")
        available_status = DomainStatus.objects.get(domain_status="Available")
        health_burned_status = HealthStatus.objects.get(health_status="Burned")
        for domain in domain_queryset:
            # Check if a domain in the library is _not_ in the Namecheap response
            if not any(d["Name"] == domain.name for d in domains_list):
                logger.info("Domain %s is not in the Namecheap data", domain.name)
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
                        domain.expiration = domain.expiration - timedelta(days=365)
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

                    _ = DomainNote.objects.create(
                        domain=domain,
                        note="Automatically set to Expired because the domain did not appear in Namecheap during a sync.",
                    )
            # Catch domains that were marked as expired but are now back in the Namecheap data
            else:
                if domain.expired:
                    logger.info("Domain %s is marked as expired but is now back in the Namecheap data", domain.name)
                    domain_changes["updates"][domain.id] = {}
                    domain_changes["updates"][domain.id]["domain"] = domain.name
                    domain_changes["updates"][domain.id]["change"] = "renewed"
                    domain.expired = False
                    if domain.domain_status == expired_status:
                        domain.domain_status = available_status
                    domain.save()

        # Now, loop over every domain returned by Namecheap
        for domain in domains_list:
            logger.info("Domain %s is now being processed", domain["Name"])

            # Prepare domain attributes for Domain model
            entry = {"name": domain["Name"], "registrar": "Namecheap"}

            # Set the WHOIS status based on WhoisGuard
            if domain["IsExpired"] == "true":
                entry["expired"] = True
                # Expired domains have WhoisGuard set to ``NOTPRESENT``
                entry["whois_status"] = WhoisStatus.objects.get(pk=2)
                entry["domain_status"] = expired_status
            else:
                if domain["WhoisGuard"].lower() == "notpresent":
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
                logger.warning("Domain %s is marked as LOCKED by Namecheap", domain["Name"])
                newly_burned = True
                entry["health_status"] = health_burned_status
                entry["domain_status"] = burned_status
                entry[
                    "burned_explanation"
                ] = "<p>Namecheap has locked the domain. This is usually the result of a legal complaint related to phishing/malicious activities.</p>"

            # Set AutoRenew status
            # Ignore Namecheap's `AutoRenew` value if the domain is expired (both can be true)
            if domain["AutoRenew"] == "false" or domain["IsExpired"] == "true":
                entry["auto_renew"] = False
            # Ensure the domain's auto-renew status in the database matches Namecheap
            elif domain["AutoRenew"] == "true":
                entry["auto_renew"] = True

            # Convert Namecheap dates to Django
            entry["creation"] = datetime.strptime(domain["Created"], "%m/%d/%Y").strftime("%Y-%m-%d")
            entry["expiration"] = datetime.strptime(domain["Expires"], "%m/%d/%Y").strftime("%Y-%m-%d")

            # Update or create the domain record with assigned attrs
            try:
                instance, created = Domain.objects.update_or_create(name=domain.get("Name"), defaults=entry)
                for attr, value in entry.items():
                    setattr(instance, attr, value)

                logger.debug("Domain %s is being saved with this data: %s", domain["Name"], entry)
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
            datetime.now(),
            domain_changes,
        )
    else:
        logger.warning("No domains were returned for the provided Namecheap account!")

    return domain_changes


def months_between(date1, date2):
    """
    Compare two dates and return the number of months between them.

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
    if isinstance(dt, datetime):
        return str(dt)
    return None


def review_cloud_infrastructure(aws_only_running=False, do_only_running=False):
    """
    Fetch active virtual machines/instances in Digital Ocean, Azure, and AWS and
    compare IP addresses to project infrastructure. Send a report to Slack if any
    instances are still alive after project end date or if an IP address is not found
    for a project.

    Returns a dictionary of cloud assets and encountered errors.

    **Parameters**

    ``aws_only_running``
        Filter out any shutdown AWS resources, where possible (Default: False)
    ``do_only_running``
        Filter out any shutdown Digital Ocean resources, where possible (Default: False)
    """
    # Fetch cloud API keys and tokens
    cloud_config = CloudServicesConfiguration.get_solo()
    ignore_tags = []
    for tag in cloud_config.ignore_tag.split(","):
        ignore_tags.append(tag.strip())
    logger.info("Ignoring tags: %s", ignore_tags)

    # Fetch Slack configuration information
    slack = SlackNotification()

    # Create info dict
    vps_info = defaultdict()
    vps_info["errors"] = {}
    vps_info["instances"] = {}

    logger.info("Starting review of cloud infrastructure at %s", datetime.now())

    ###############
    # AWS Section #
    ###############

    # Test connection with STS
    results = test_aws(cloud_config.aws_key, cloud_config.aws_secret)
    aws_capable = results["capable"]
    if aws_capable:
        logger.info("AWS credentials are functional so beginning AWS review")

        # Check EC2
        logger.info("Checking EC2 instances")
        ec2_results = fetch_aws_ec2(cloud_config.aws_key, cloud_config.aws_secret, ignore_tags, aws_only_running)
        if ec2_results["message"]:
            vps_info["errors"]["ec2"] = ec2_results["message"]
        for instance in ec2_results["instances"]:
            vps_info["instances"][instance["id"]] = instance

        # Check Lightsail
        logger.info("Checking Lightsail instances")
        lightsail_results = fetch_aws_lightsail(cloud_config.aws_key, cloud_config.aws_secret, ignore_tags)
        if lightsail_results["message"]:
            vps_info["errors"]["lightsail"] = lightsail_results["message"]
        for instance in lightsail_results["instances"]:
            vps_info["instances"][instance["id"]] = instance

        # Check S3
        logger.info("Checking S3 buckets")
        s3_results = fetch_aws_s3(cloud_config.aws_key, cloud_config.aws_secret)
        if s3_results["message"]:
            vps_info["errors"]["s3"] = s3_results["message"]
        for bucket in s3_results["buckets"]:
            vps_info["instances"][bucket["name"]] = bucket
    else:
        vps_info["errors"]["aws"] = results["message"]

    ###############
    # DO Section  #
    ###############

    logger.info("Checking Digital Ocean droplets")
    do_results = fetch_digital_ocean(cloud_config.do_api_key, ignore_tags, do_only_running)
    if do_results["message"]:
        vps_info["errors"]["digital_ocean"] = do_results["message"]
    else:
        if do_results["capable"]:
            for instance in do_results["instances"]:
                vps_info["instances"][instance["id"]] = instance

    ##################
    # Notifications  #
    ##################

    # Examine results to identify potentially unneeded/unused machines
    assets_in_use = []
    for instance_id, instance in vps_info["instances"].items():
        all_ip_addresses = []
        if "public_ip" in instance:
            for address in instance["public_ip"]:
                if address is not None:
                    all_ip_addresses.append(address)
        if "private_ip" in instance:
            for address in instance["private_ip"]:
                if address is not None:
                    all_ip_addresses.append(address)
        # Set instance's name to its ID if no name is set
        if instance["name"]:
            instance_name = instance["name"]
        else:
            instance_name = instance["id"]
        # Check if any IP address is associated with a project
        queryset = TransientServer.objects.select_related("project").filter(
            Q(ip_address__in=all_ip_addresses) | Q(aux_address__overlap=all_ip_addresses)
        )
        if queryset:
            for result in queryset:
                # Consider the asset in use if the project's end date is in the past
                if result.project.end_date + timedelta(days=cloud_config.notification_delay) <= date.today():
                    logger.info(
                        "Project end date is %s which is earlier than now, %s",
                        result.project.end_date,
                        datetime.now().date(),
                    )
                    if slack.enabled:
                        blocks = slack.craft_cloud_msg(
                            instance["launch_time"],
                            result.project,
                            result.project.end_date,
                            instance["provider"],
                            instance_name,
                            instance["public_ip"],
                            instance["tags"],
                            instance["state"],
                        )
                        if result.project.slack_channel:
                            err = slack.send_msg(
                                message=f"Teardown notification for {result.project}",
                                channel=result.project.slack_channel,
                                blocks=blocks,
                            )
                        else:
                            err = slack.send_msg(
                                message=f"Teardown notification for {result.project}",
                                blocks=blocks,
                            )
                        if err:
                            logger.warning(
                                "Attempt to send a Slack notification returned an error: %s",
                                err,
                            )
                else:
                    # Project is still active, so track these assets for later
                    assets_in_use.append(instance_id)
        else:
            instance_tags = []
            for tag in instance["tags"].split(","):
                instance_tags.append(tag.strip())
            if instance["ignore"]:
                logger.info(
                    "Ignoring %s because it is tagged with a configured ignore tag (tags: %s)",
                    instance_name,
                    instance["tags"],
                )
                assets_in_use.append(instance_id)
            else:
                if slack.enabled:
                    blocks = slack.craft_unknown_asset_msg(
                        instance["launch_time"],
                        instance["provider"],
                        instance_name,
                        instance["public_ip"],
                        instance["tags"],
                        instance["state"],
                    )
                    err = slack.send_msg(
                        message="Untracked cloud asset found",
                        blocks=blocks,
                    )
                    if err:
                        logger.warning(
                            "Attempt to send a Slack notification returned an error: %s",
                            err,
                        )

    # Return the stale cloud asset data in JSON for the task results
    json_data = json.dumps(dict(vps_info), default=json_datetime_converter, indent=2)
    logger.info("Cloud review completed at %s", datetime.now())
    logger.debug("JSON results:\n%s", json_data)
    return json_data


def check_expiration():
    """
    Update expiration status for all :model:`shepherd.Domain`.
    """
    domain_changes = {"errors": {}, "updates": {}}
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
                domain.expiration = domain.expiration + timedelta(days=365)
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

    logger.info("Domain expiration update completed at %s", datetime.now())
    return domain_changes


def test_aws_keys(user):
    """
    Test the AWS access keys configured in :model:`commandcenter.CloudServicesConfiguration`.
    """
    cloud_config = CloudServicesConfiguration.get_solo()

    logger.info("Starting a test of the AWS keys at %s", datetime.now())

    results = test_aws(cloud_config.aws_key, cloud_config.aws_secret)

    if results["capable"]:
        logger.info("Successfully verified the AWS keys")
        message = "Successfully verified the AWS keys"
        level = "success"
    else:
        logger.error("AWS could not validate the provided credentials")
        message = results["message"]
        level = "error"

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

    logger.info("Test of the AWS access keys completed at %s", datetime.now())
    return {"result": level, "message": message}


def test_digital_ocean(user):
    """
    Test the Digital Ocean API key configured in
    :model:`commandcenter.CloudServicesConfiguration`.
    """
    digital_ocean_endpoint = "https://api.digitalocean.com/v2/droplets"
    cloud_config = CloudServicesConfiguration.get_solo()
    level = "error"
    logger.info("Starting a test of the Digital Ocean API key at %s", datetime.now())
    try:
        # Request all active droplets (as done in the real task)
        headers = {"Content-Type": "application/json"}
        active_droplets = requests.get(
            digital_ocean_endpoint,
            headers=headers,
            auth=BearerAuth(cloud_config.do_api_key),
        )
        if active_droplets.status_code == 200:
            logger.info("Digital Ocean credentials are functional, beginning droplet review")
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

    logger.info("Test of the Digital Ocean API key completed at %s", datetime.now())
    return {"result": level, "message": message}


def test_namecheap(user):
    """
    Test the Namecheap API configuration stored in :model:`commandcenter.NamecheapConfiguration`.
    """
    session = requests.Session()
    get_domain_list_endpoint = "https://api.namecheap.com/xml.response?ApiUser={}&ApiKey={}&UserName={}&Command=namecheap.domains.getList&ClientIp={}&PageSize={}"
    namecheap_config = NamecheapConfiguration.get_solo()
    level = "error"
    logger.info("Starting Namecheap API test at %s", datetime.now())
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
            # Convert Namecheap XML into an easy-to-use object for iteration
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
                message = "Namecheap returned a {namecheap_api_result} response: {req.text}"
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
        datetime.now(),
    )
    return {"result": level, "message": message}


def test_slack_webhook(user):
    """
    Test the Slack Webhook configuration stored in :model:`commandcenter.SlackConfiguration`.
    """
    level = "error"
    slack = SlackNotification()
    logger.info("Starting Slack Webhook test at %s", datetime.now())
    try:
        err = slack.send_msg("Hello from Ghostwriter :wave:")
        if err:
            level = "error"
            message = err["message"]
        else:
            level = "success"
            message = f"Slack accepted the request and you should see a message posted in {slack.slack_channel}"
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

    logger.info("Test of the Slack Webhook completed at %s", datetime.now())
    return {"result": level, "message": message}


def test_virustotal(user):
    """
    Test the VirusTotal API key stored in :model:`commandcenter.VirusTotalConfiguration`.
    """
    virustotal_config = VirusTotalConfiguration.get_solo()
    level = "error"
    logger.info("Starting VirusTotal API test at %s", datetime.now())
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
            logger.warning("Received request to test the VirusTotal API key, but VirusTotal is disabled in settings")
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

    logger.info("Test of the VirusTotal completed at %s", datetime.now())
    return {"result": level, "message": message}
