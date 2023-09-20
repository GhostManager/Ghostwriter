"""This contains all of functions for checking cloud services."""

# Standard Libraries
import logging
import traceback
from datetime import datetime

# 3rd Party Libraries
import boto3
import pytz
import requests
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectTimeoutError

# Using __name__ resolves to ghostwriter.modules.cloud_monitors
logger = logging.getLogger(__name__)

# Set timezone for dates to UTC
utc = pytz.UTC

# Digital Ocean API endpoint for droplets
digital_ocean_endpoint = "https://api.digitalocean.com/v2/droplets"


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


def test_aws(aws_key, aws_secret):
    """
    Test AWS keys by connecting to STS and calling ``get_caller_identity``.

    **Parameters**

    ``aws_key``
        AWS key with access to the service
    ``aws_secret``
        AWS secret for the key
    """
    messages = []
    try:
        aws_sts = boto3.client(
            "sts",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
        )
        aws_sts.get_caller_identity()
        return {"capable": True, "message": messages}
    except ClientError:
        logger.error("AWS could not validate the provided credentials with STS; check your AWS policies")
        messages.append("AWS could not validate the provided credentials for EC2; check your attached AWS policies")
    except Exception:
        logger.exception("Testing authentication to AWS failed")
        messages.append(f"Testing authentication to AWS failed: {traceback.format_exc()}")
    return {"capable": False, "message": messages}


def fetch_aws_ec2(aws_key, aws_secret, ignore_tags=None, only_running=False):
    """
    Authenticate to the AWS EC2 service and fetch all instances.

    **Parameters**

    ``only_running``
        If ``True``, only return running instances
    ``ignore_tags``
        List of tags to ignore when fetching instances
    ``aws_key``
        AWS key with access to the service
    ``aws_secret``
        AWS secret for the key
    """
    messages = []
    instances = []
    if ignore_tags is None:
        ignore_tags = []
    try:
        ec2_config = Config(
            retries={
                "max_attempts": 1,
                "mode": "standard",
            },
            connect_timeout=30,
        )
        client = boto3.client(
            "ec2",
            region_name="us-west-2",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            config=ec2_config,
        )
        regions = [region["RegionName"] for region in client.describe_regions()["Regions"]]
        # Loop over the regions to check each one for EC2 instances
        for region in regions:
            logger.info("Checking AWS region %s for EC2", region)
            # Create an EC2 resource for the region
            ec2 = boto3.resource(
                "ec2",
                region_name=region,
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                config=ec2_config,
            )
            # Get all EC2 instances that are running
            if only_running:
                running_instances = ec2.instances.filter(
                    Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                )
            else:
                running_instances = ec2.instances.all()
            # Loop over running instances to generate info dict
            try:
                for instance in running_instances:
                    # Calculate how long the instance has been running in UTC
                    time_up = months_between(
                        instance.launch_time.replace(tzinfo=utc),
                        datetime.today().replace(tzinfo=utc),
                    )
                    tags = []
                    name = "Blank"
                    ignore = False
                    if instance.tags:
                        for tag in instance.tags:
                            # AWS assigns names to instances via a ``Name`` key
                            if tag["Key"] == "Name":
                                name = tag["Value"]
                            else:
                                tags.append("{}: {}".format(tag["Key"], tag["Value"]))
                            # Check for "ignore tags"
                            if tag["Key"] in ignore_tags or tag["Value"] in ignore_tags:
                                ignore = True
                    pub_addresses = []
                    if instance.public_ip_address:
                        pub_addresses.append(instance.public_ip_address)
                    priv_addresses = []
                    if instance.private_ip_address:
                        priv_addresses.append(instance.private_ip_address)
                    # Add instance info to a dictionary
                    instances.append(
                        {
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
                            "ignore": ignore,
                        }
                    )
            except ConnectTimeoutError:
                logger.exception("AWS timed out while trying to describe instances in %s", region)
                messages.append(
                    f"AWS timed out while trying to describe instances in {region}: {traceback.format_exc()}"
                )
    except ClientError:
        logger.error("AWS denied access to EC2 for the supplied keys; check your AWS policies")
        messages.append("AWS denied access to EC2 for the supplied keys; check your attached AWS policies")
    except ConnectTimeoutError:
        logger.exception("AWS timed out while connecting to EC2 region")
        messages.append(f"AWS timed out while connecting to EC2 region: {traceback.format_exc()}")
    except Exception:
        logger.exception("Encountered an unexpected error with AWS EC2")
        messages.append(f"Encountered an unexpected error with AWS EC2: {traceback.format_exc()}")
    return {"instances": instances, "message": messages}


def fetch_aws_lightsail(aws_key, aws_secret, ignore_tags=None):
    """
    Authenticate to AWS Lightsail and fetch all instances.


    **Parameters**

    ``aws_key``
        AWS key with access to the service
    ``aws_secret``
        AWS secret for the key
    ``ignore_tags``
        List of tags to ignore for instance filtering
    """
    message = ""
    instances = []
    if ignore_tags is None:
        ignore_tags = []
    try:
        # Get all Lightsail instances using the low-level client (no resource option available)
        # Ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lightsail.html#Lightsail.Client.get_instances
        default_lightsail = boto3.client(
            "lightsail",
            region_name="us-west-2",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
        )
        regions = [region["name"] for region in default_lightsail.get_regions()["regions"]]

        for region in regions:
            logger.info("Checking AWS region %s for Lightsail", region)
            # Create an EC2 resource for the region
            lightsail = boto3.client(
                "lightsail",
                region_name=region,
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
            )
            # Get all instances that are running
            running_instances = lightsail.get_instances()
            # Loop over running instances to generate info dict
            for instance in running_instances["instances"]:
                # Calculate how long the instance has been running in UTC
                time_up = months_between(
                    instance["createdAt"].replace(tzinfo=utc),
                    datetime.today().replace(tzinfo=utc),
                )
                tags = []
                name = "Blank"
                ignore = False
                if instance["tags"]:
                    for tag in instance["tags"]:
                        # AWS assigns names to instances via a ``Name`` key
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                        else:
                            tags.append("{}: {}".format(tag["Key"], tag["Value"]))
                        # Check for "ignore tags"
                        if tag["Key"] in ignore_tags or tag["Value"] in ignore_tags:
                            ignore = True
                pub_addresses = [instance["publicIpAddress"]]
                priv_addresses = [instance["privateIpAddress"]]
                # Add instance info to a dictionary
                instances.append(
                    {
                        "id": instance["name"],
                        "provider": "Amazon Web Services {}".format(region),
                        "service": "Lightsail",
                        "name": name,
                        "type": instance["resourceType"],
                        "monthly_cost": None,  # AWS cost is different and not easily calculated
                        "cost_to_date": None,  # AWS cost is different and not easily calculated
                        "state": instance["state"]["name"],
                        "private_ip": priv_addresses,
                        "public_ip": pub_addresses,
                        "launch_time": instance["createdAt"].replace(tzinfo=utc),
                        "time_up": "{} months".format(time_up),
                        "tags": ", ".join(tags),
                        "ignore": ignore,
                    }
                )
    except ClientError:
        logger.error("AWS denied access to Lightsail for the supplied keys; check your AWS policies")
        message = "AWS denied access to Lightsail for the supplied keys; check your attached AWS policies"
    except Exception:
        logger.exception("Encountered an unexpected error with AWS Lightsail")
        message = f"Encountered an unexpected error with AWS Lightsail: {traceback.format_exc()}"
    return {"instances": instances, "message": message}


def fetch_aws_s3(aws_key, aws_secret, ignore_tags=None):
    """
    Authenticate to the AWS S3 service and fetch the names of all buckets.

    **Parameters**

    ``aws_key``
        AWS key with access to the service
    ``aws_secret``
        AWS secret for the key
    ``ignore_tags``
        List of tags to ignore for bucket filtering
    """
    message = ""
    buckets = []
    if ignore_tags is None:
        ignore_tags = []
    try:
        logger.info("Collecting bucket resources from AWS S3")
        # Create an S3 client
        s3 = boto3.client(
            "s3",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
        )

        # List all buckets
        bucket_iterator = s3.list_buckets()

        for bucket in bucket_iterator["Buckets"]:
            # Ignore is hard-coded to True for now – until S3 buckets are trackable
            ignore = True
            time_up = months_between(
                bucket["CreationDate"].replace(tzinfo=utc),
                datetime.today().replace(tzinfo=utc),
            )
            buckets.append(
                {
                    "id": bucket["Name"],
                    "provider": "Amazon Web Services",
                    "service": "S3",
                    "name": bucket["Name"],
                    "type": "Bucket",
                    "monthly_cost": None,  # AWS cost is different and not easily calculated
                    "cost_to_date": None,  # AWS cost is different and not easily calculated
                    "state": None,
                    "private_ip": [],
                    "public_ip": [],
                    "launch_time": bucket["CreationDate"].replace(tzinfo=utc),
                    "time_up": "{} months".format(time_up),
                    "tags": "N/A",
                    "ignore": ignore,
                }
            )
    except ClientError:
        logger.error("AWS denied access to S3 for the supplied keys; check your AWS policies")
        message = "AWS denied access to S3 for the supplied keys; check your attached AWS policies"
    except Exception:
        logger.exception("Encountered an unexpected error with AWS S3")
        message = f"Encountered an unexpected error with AWS S3: {traceback.format_exc()}"
    return {"buckets": buckets, "message": message}


def fetch_digital_ocean(api_key, ignore_tags=None, do_only_running=False):
    """
    Authenticate to Digital Ocean and fetch all droplets.


    **Parameters**

    ``api_key``
        API key for the service
    ``ignore_tags``
        List of tags to ignore for instance filtering
    """
    message = ""
    instances = []
    capable = False
    active_droplets = None
    if ignore_tags is None:
        ignore_tags = []

    headers = {"Content-Type": "application/json"}
    try:
        active_droplets = requests.get(
            digital_ocean_endpoint,
            headers=headers,
            auth=BearerAuth(api_key),
        )
        if active_droplets.status_code == 200:
            capable = True
            active_droplets = active_droplets.json()
            logger.info("Digital Ocean credentials are functional, beginning droplet review")

            if do_only_running:
                active_droplets["droplets"] = [
                    droplet for droplet in active_droplets["droplets"] if droplet["status"] == "active"
                ]
        else:
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
            message = f"Digital Ocean API request failed with this response: {api_response}"
    # Catch a JSON decoding error with the response
    except ValueError:
        logger.exception("Could not decode the response from Digital Ocean")
        message = f"Could not decode this response from Digital Ocean: {active_droplets.text}"
    # Catch any other errors related to the web request
    except Exception:
        logger.exception("Encountered an unexpected error with Digital Ocean")
        message = f"Encountered an unexpected error with Digital Ocean: {traceback.format_exc()}"

    # Loop over the droplets to generate the info dict
    if capable and "droplets" in active_droplets:
        for droplet in active_droplets["droplets"]:
            ignore = False
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
                datetime.strptime(droplet["created_at"].split("T")[0], "%Y-%m-%d").replace(tzinfo=utc),
                datetime.today().replace(tzinfo=utc),
            )
            cost_to_date = (
                months_between(
                    datetime.strptime(droplet["created_at"].split("T")[0], "%Y-%m-%d"),
                    datetime.today(),
                )
                * droplet["size"]["price_monthly"]
            )
            # Check for "ignore tags"
            for tag in droplet["tags"]:
                if tag in ignore_tags:
                    ignore = True
            # Add an entry to the dict for the droplet
            instances.append(
                {
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
                    "launch_time": datetime.strptime(droplet["created_at"].split("T")[0], "%Y-%m-%d").replace(
                        tzinfo=utc
                    ),
                    "time_up": "{} months".format(time_up),
                    "tags": ", ".join(droplet["tags"]),
                    "ignore": ignore,
                }
            )

    return {"capable": capable, "message": message, "instances": instances}
