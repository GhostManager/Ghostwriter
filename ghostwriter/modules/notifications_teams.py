# Standard Libraries
import json
import logging
from typing import Union

# 3rd Party Libraries
import requests

# Django Imports
from django.urls import reverse
from django_q.models import Task

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import NotificationsConfiguration

# Using __name__ resolves to ghostwriter.shepherd.tasks
logger = logging.getLogger(__name__)


class TeamsNotification:
    """Compose and send Teams messages for notifications."""

    def __init__(self):
        teams_config = NotificationsConfiguration.get_solo()
        self.enabled = teams_config.teams_enable
        self.teams_webhook_url = teams_config.teams_webhook_url

    def send_msg(self, message: str, blocks: list = None) -> dict:
        """
        Send card to the provided webhook channel. Returns a dictionary
        with errors, if any. The dictionary includes ``code`` and ``message`` keys.

        **Parameters**

        ``message``
            Plain text string to be sent as the Teams message
        """
        error = {}

        if self.enabled:
            # Create Teams message card to send to the channel
            if blocks:
                teams_card = {
                    "@type": "MessageCard",
                    "@context": "http://schema.org/extensions",
                    "themeColor": "0076D7",
                    "summary": f"{message}",
                    "sections": blocks
                }
            else:
                teams_card = {
                    "text": f"{message}"
                }
            try:
                # Post the message to Teams
                response = requests.post(
                    self.teams_webhook_url,
                    data=json.dumps(teams_card),
                    headers={"Content-Type": "application/json"},
                )
                # Responses for Incoming Webhooks are documented here:
                # https://api.Teams.com/changelog/2016-05-17-changes-to-errors-for-incoming-webhooks
                if response.ok:
                    logger.info("Teams message sent successfully")
                # Handle and log any unexpected response codes
                else:
                    logger.warning(
                        "Request to Teams returned HTTP code %s with this message: %s",
                        response.status_code,
                        response.text,
                    )
                    error["code"] = "unknown_error"
                    error[
                        "message"
                    ] = f"Request to Teams returned HTTP code {response.status_code} with this message: {response.text}"
            except Exception as e:
                logger.warning("Request to Teams failed with this message: %s", str(e))
                error["code"] = "request_failed"
                error["message"] = f"Request to Teams failed with this message: {str(e)}"
        else:
            logger.warning("Received request to send Teams message, but Teams notifications are disabled in settings")
            error["code"] = "teams_disabled"
            error[
                "message"
            ] = "Received request to send Teams message, but Teams notifications are disabled in settings"

        return error

    def craft_cloud_msg(
        self,
        launch_time: str,
        project_name: str,
        end_date: str,
        cloud_provider: str,
        vps_name: str,
        ip_address: Union[str, list],
        tags: str,
    ) -> list:
        """
        Create the blocks for a nicely formatted Teams message for cloud asset notifications.

        **Parameters**

        ``launch_time``
            Date and time the cloud asset was launched
        ``project_name``
            Name of the project associated with the cloud asset
        ``end_date``
            Date the cloud asset is scheduled to be terminated
        ``cloud_provider``
            Cloud asset's hosting provider
        ``vps_name``
            Name of the cloud asset
        ``ip_address``
            IP address of the cloud asset
        ``tags``
            Any tags associated with the cloud asset
        """
        if ip_address:
            if isinstance(ip_address, list):
                ip_address = ", ".join(filter(None, ip_address))
        else:
            ip_address = "None Assigned"

        if not tags:
            tags = "None Assigned"

        blocks = [{
            "activityTitle": f"{project_name}",
            "activitySubtitle": "Cloud Teardown Notification",
            "facts": [
                {
                    "name":  "Cloud Provider",
                    "value": f"{cloud_provider}"
                },
                {
                    "name": "Instance Name",
                    "value": f"{vps_name}"
                },
                {
                    "name": "Ext IP Address",
                    "value": f"{ip_address}"
                },
                {
                    "name": "Launch Date",
                    "value": f"{launch_time}"
                },
                {
                    "name": "Project End Date",
                    "value": f"{end_date}"
                },
                {
                    "name": "Tags",
                    "value": f"{tags}"
                }
                ],
            },
        ]
        return blocks

    def craft_unknown_asset_msg(
        self,
        launch_time: str,
        cloud_provider: str,
        vps_name: str,
        ip_address: Union[str, list],
        tags: str,
    ) -> list:
        """
        Create the blocks for a nicely formatted Teams message for unknown cloud asset notifications.


        **Parameters**

        ``launch_time``
            Date and time the cloud asset was launched
        ``cloud_provider``
            Cloud asset's hosting provider
        ``vps_name``
            Name of the cloud asset
        ``ip_address``
            IP address of the cloud asset
        ``tags``
            Any tags associated with the cloud asset
        """
        if ip_address:
            if isinstance(ip_address, list):
                ip_address = ", ".join(filter(None, ip_address))
        else:
            ip_address = "None Assigned"

        if not tags:
            tags = "None Assigned"

        blocks = [{
            "activityTitle": "Untracked Cloud Server",
            "activitySubtitle": "An *untracked* cloud asset is running without being attached to a project. If this asset should be ignored, tag it with one of the configured `Ignore Tags` in settings.",
            "facts": [
                {
                    "name":  "Cloud Provider",
                    "value": f"{cloud_provider}"
                },
                {
                    "name": "Instance Name",
                    "value": f"{vps_name}"
                },
                {
                    "name": "Ext IP Address",
                    "value": f"{ip_address}"
                },
                {
                    "name": "Launch Date",
                    "value": f"{launch_time}"
                },
                {
                    "name": "Tags",
                    "value": f"{tags}"
                }
                ],
            },
        ]
        return blocks

    def craft_burned_msg(
        self,
        domain: str,
        categories: str,
        burned_explanation: str,
    ) -> list:
        """
        Create the blocks for a nicely formatted Teams message for burned domain notifications.

        **Parameters**

        ``domain``
            Name of the burned domain
        ``categories``
            Categories associated with the domain
        ``burned_explanation``
            Explanation of why the domain was burned
        """
        blocks = [{
            "activityTitle": "Domain Burned",
            "activitySubtitle": "Warning",
            "facts": [
                {
                    "name":  "Domain Name",
                    "value": f"{domain}"
                },
                {
                    "name": "Categories",
                    "value": f"{categories}"
                },
                {
                    "name": "Reason",
                    "value": "\n".join(burned_explanation)
                }
                ],
            },
        ]
        return blocks

    def craft_warning_msg(
        self,
        domain: str,
        warning_type: str,
        warnings: str,
    ) -> list:
        """
        Create the blocks for a nicely formatted Teams message for domain warning notifications.

        **Parameters**

        ``domain``
            Name of the domain
        ``warning_type``
            Type of warning
        ``warnings``
            Explanation of the warning
        """
        blocks = [{
            "activityTitle": "Domain Event",
            "activitySubtitle": "Warning",
            "facts": [
                {
                    "name":  "Domain Name",
                    "value": f"{domain}"
                },
                {
                    "name": "Warning",
                    "value": f"{warning_type}"
                },
                {
                    "name": "Reason",
                    "value": "\n".join(warnings)
                }
                ],
            },
        ]
        return blocks

    def craft_inactive_log_msg(
        self, oplog: str, project: str, hours_inactive: int, last_entry_date: str = None
    ) -> list:
        """
        Create the blocks for a nicely formatted Teams message for inactive oplog notifications.

        **Parameters**

        ``oplog``
            Name of the oplog
        ``project``
            Name of the project associated with the oplog
        ``last_entry_date``
            Date of the last entry in the oplog
        """
        if last_entry_date:
            last_entry_date = f"Last entry was submitted on {last_entry_date} UTC."
        else:
            last_entry_date = "The log contained no entries during this review."
        blocks = [{
            "activityTitle": "Logging Inactive",
            "activitySubtitle": "Warning",
            "facts": [
                {
                    "name": "Oplog",
                    "value": f"{oplog}"
                },
                {
                    "name": "Project",
                    "value": f"{project}"
                },
                {
                    "name": "Info",
                    "value": f"The log has been inactive for at least {hours_inactive}. If this is unexpected, please check the log."
                },
                {
                    "name": "Last Entry",
                    "value": f"{last_entry_date}"
                }
                ],
            },
        ]
        return blocks


def send_teams_complete_msg(task: Task) -> None:
    """
    Send a basic Teams message using the global Teams configuration upon completion
    of an :model:`django_q.Task`.

    **Parameters**

    ``task``
        Instance of :model:`django_q.Task`
    """
    logger.info("Sending Teams message for completed task %s", task.id)

    teams = TeamsNotification()

    if task.success:
        task_url = reverse("admin:django_q_success_change", args=(task.id,))
    else:
        task_url = reverse("admin:django_q_failure_change", args=(task.id,))

    # Blocks for Teams messages – combine lists to assemble the message
    success_blocks = [{
        "activityTitle": f"{task.group} task successfully completed its run",
        "activitySubtitle": "Successful task run",
        "facts": [
            {
                "name":  "Details",
                "value": f"Details and task output can be viewed in the admin panel under:\n _{task_url}_",
            }
            ],
        },
    ]

    failure_blocks = [{
        "activityTitle":f"*{task.group}* task failed",
        "activitySubtitle": "Failed task run",
        "facts": [
            {
                "name":  "Details",
                "value": f"Details and task output can be viewed in the admin panel under:\n _{task_url}_",
            }
            ],
        },
    ]

    try:
        # Assemble blocks based on task results and send the message
        if task.success:
            err = teams.send_msg(
                "Task successful",
                blocks=success_blocks,
            )
        else:
            err = teams.send_msg("Task failed", blocks=failure_blocks)

        if err:
            logger.warning("Attempt to send a Teams notification returned an error: %s", err)
    except Exception:
        logger.exception("Error sending Teams message")
