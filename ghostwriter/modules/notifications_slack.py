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
from ghostwriter.commandcenter.models import SlackConfiguration

# Using __name__ resolves to ghostwriter.shepherd.tasks
logger = logging.getLogger(__name__)


class SlackNotification:
    """Compose and send Slack messages for notifications."""

    def __init__(self):
        slack_config = SlackConfiguration.get_solo()
        self.enabled = slack_config.enable
        self.slack_webhook_url = slack_config.webhook_url
        self.slack_username = slack_config.slack_username
        self.slack_emoji = slack_config.slack_emoji
        self.slack_channel = slack_config.slack_channel
        self.slack_alert_target = slack_config.slack_alert_target

    def send_msg(self, message: str, channel: str = None, blocks: list = None) -> dict:
        """
        Send a basic Slack message using the Slack configuration. Returns a dictionary
        with errors, if any. The dictionary includes ``code`` and ``message`` keys.

        **Parameters**

        ``message``
            Plain text string to be sent as the Slack message
        ``channel``
            Name of a Slack user or channel (e.g., ``@username`` or ``#channel``; Defaults to configured global channel)
        ``blocks``
            List of Slack content "blocks" to be included with the message (see https://api.slack.com/reference/block-kit/blocks)
        """
        error = {}

        if self.enabled:
            # Use the global Slack channel if none is specified
            if not channel:
                channel = self.slack_channel

            # Append the alert target to the message if it's set
            if self.slack_alert_target:
                message = f"{self.slack_alert_target} {message}"

            # Assemble the complete Slack POST data
            slack_data = {
                "username": self.slack_username,
                "icon_emoji": self.slack_emoji,
                "channel": channel,
                "text": message,
                "blocks": blocks,
            }
            try:
                # Post the message to Slack
                response = requests.post(
                    self.slack_webhook_url,
                    data=json.dumps(slack_data),
                    headers={"Content-Type": "application/json"},
                )
                # Responses for Incoming Webhooks are documented here:
                # https://api.slack.com/changelog/2016-05-17-changes-to-errors-for-incoming-webhooks
                if response.ok:
                    logger.info("Slack message sent successfully")
                elif response.status_code == 400:
                    if "user_not_found" in response.text:
                        error["code"] = "user_not_found"
                        error[
                            "message"
                        ] = f"Slack accepted the request, but said the user/channel {channel} does not exist"
                    else:
                        error["code"] = "invalid_payload"
                        error[
                            "message"
                        ] = f"Slack accepted the request, but said this payload was invalid: {json.dumps(slack_data)}"
                elif response.status_code == 403:
                    if "invalid_token" in response.text:
                        error["code"] = "invalid_token"
                        error["message"] = "Slack accepted the request, but said your Webhook token is invalid"
                    elif "action_prohibited" in response.text:
                        error["code"] = "action_prohibited"
                        error[
                            "message"
                        ] = f"Slack accepted the request, but said your Webhook token cannot send messages to {channel}, or is otherwise restricted"
                elif response.status_code == 404:
                    error["code"] = "channel_not_found"
                    error[
                        "message"
                    ] = f"Slack accepted the request, but said it could not find the user/channel {channel}"
                elif response.status_code == 410:
                    if "channel_is_archived" in response.text:
                        error["code"] = "channel_is_archived"
                        error["message"] = f"Slack accepted the request, but said the {channel} channel is archived"
                elif response.status_code == 500:
                    error["code"] = "server_error"
                    error["message"] = "Slack's server encountered an internal server error"
                # Handle and log any unexpected response codes
                else:
                    logger.warning(
                        "Request to Slack returned HTTP code %s with this message: %s",
                        response.status_code,
                        response.text,
                    )
                    error["code"] = "unknown_error"
                    error[
                        "message"
                    ] = f"Request to Slack returned HTTP code {response.status_code} with this message: {response.text}"
            except Exception as e:
                logger.warning("Request to Slack failed with this message: %s", str(e))
                error["code"] = "request_failed"
                error["message"] = f"Request to Slack failed with this message: {str(e)}"
        else:
            logger.warning("Received request to send Slack message, but Slack notifications are disabled in settings")
            error["code"] = "slack_disabled"
            error[
                "message"
            ] = "Received request to send Slack message, but Slack notifications are disabled in settings"

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
        Create the blocks for a nicely formatted Slack message for cloud asset notifications.

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

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":cloud: Teardown Notification for {project_name} :cloud:",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Cloud Provider:*\n{cloud_provider}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Instance Name:*\n{vps_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Ext IP Address:*\n{ip_address}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Launch Date:*\n{launch_time}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Project End Date:*\n{end_date}",
                    },
                    {"type": "mrkdwn", "text": f"*Tags:*\n{tags}"},
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
        Create the blocks for a nicely formatted Slack message for unknown cloud asset notifications.


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

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":eyes: Untracked Cloud Server :eyes:",
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
                        "text": f"*Cloud Provider:*\n{cloud_provider}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Instance Name:*\n{vps_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Ext IP Address:*\n{ip_address}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Launch Date:*\n{launch_time}",
                    },
                    {"type": "mrkdwn", "text": f"*Tags:*\n{tags}"},
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
        Create the blocks for a nicely formatted Slack message for burned domain notifications.

        **Parameters**

        ``domain``
            Name of the burned domain
        ``categories``
            Categories associated with the domain
        ``burned_explanation``
            Explanation of why the domain was burned
        """
        blocks = [
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
                        "text": f"*Domain Name:*\n{domain}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Categories:*\n{categories}",
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
        ]
        return blocks

    def craft_warning_msg(
        self,
        domain: str,
        warning_type: str,
        warnings: str,
    ) -> list:
        """
        Create the blocks for a nicely formatted Slack message for domain warning notifications.

        **Parameters**

        ``domain``
            Name of the domain
        ``warning_type``
            Type of warning
        ``warnings``
            Explanation of the warning
        """
        blocks = [
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
                        "text": f"*Domain Name:*\n{domain}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Warning:*\n{warning_type}",
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
        ]
        return blocks

    def craft_inactive_log_msg(
        self, oplog: str, project: str, hours_inactive: int, last_entry_date: str = None
    ) -> list:
        """
        Create the blocks for a nicely formatted Slack message for inactive oplog notifications.

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
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":warning: Logging Inactive :warning:",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Oplog:*\n{oplog}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*\n{project}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"The log has been inactive for at least {hours_inactive}. If this is unexpected, please check the log.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{last_entry_date}",
                },
            },
        ]
        return blocks


def send_slack_complete_msg(task: Task) -> None:
    """
    Send a basic Slack message using the global Slack configuration upon completion
    of an :model:`django_q.Task`.

    **Parameters**

    ``task``
        Instance of :model:`django_q.Task`
    """
    logger.info("Sending Slack message for completed task %s", task.id)

    slack = SlackNotification()

    if task.success:
        task_url = reverse("admin:django_q_success_change", args=(task.id,))
    else:
        task_url = reverse("admin:django_q_failure_change", args=(task.id,))

    # Blocks for Slack messages – combine lists to assemble the message
    base_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Task Complete"}},
    ]

    success_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{task.group}* task successfully completed its run :smile:",
            },
        },
    ]

    failure_blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{task.group}* task failed :frowning:"},
        },
    ]

    result_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Details and task output can be viewed in the admin panel under:\n _{task_url}_",
            },
        },
    ]

    try:
        # Assemble blocks based on task results and send the message
        if task.success:
            err = slack.send_msg(
                "Task successful",
                blocks=base_blocks + success_blocks + result_blocks,
            )
        else:
            err = slack.send_msg("Task failed", blocks=base_blocks + failure_blocks + result_blocks)

        if err:
            logger.warning("Attempt to send a Slack notification returned an error: %s", err)
    except Exception:
        logger.exception("Error sending Slack message")
