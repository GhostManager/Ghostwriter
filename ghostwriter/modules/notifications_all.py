# Standard Libraries
from typing import Union

# Django Imports
from django_q.models import Task

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import NotificationsConfiguration
from ghostwriter.modules.notifications_slack import SlackNotification
from ghostwriter.modules.notifications_teams import TeamsNotification

class NotificationsCenter:
    """Generic notifications center module to send notifications to enabled services"""

    def __init__(self):
        notifications_config = NotificationsConfiguration.get_solo()
        self.slack_enabled = notifications_config.slack_enable
        self.teams_enabled = notifications_config.slack_enable
        self.enabled = False
        if self.slack_enabled:
            self.enabled = True
        if self.teams_enabled:
            self.enabled = True

    def send_msg(self, message: str, channel: str = None, blocks: list = None) -> dict:
        """
        Send a basic message to one or more of the enabled services
        """
        errors = {}
        if self.slack_enabled:
            # Initiate the SlackNotification class
            slack = SlackNotification()

            # Send the message
            slack_errors = slack.send_msg(message, channel, blocks)

            # Update the collective dictionary with errors
            errors.update(slack_errors)
        if self.teams_enabled:
            # Initiate the TeamsNotification class
            teams = TeamsNotification()

            # Send the message
            teams_errors = teams.send_msg(message, blocks)

            # Update the collective dictionary with errors
            errors.update(teams_errors)

        return errors

    def send_cloud_msg(
        self,
        launch_time: str,
        project_name: str,
        end_date: str,
        cloud_provider: str,
        vps_name: str,
        ip_address: Union[str, list],
        tags: str,
        message: str,
        slack_channel: str = None,
    ) -> dict:
        """
        Create the blocks for a nicely formatted Slack or Teams message for cloud asset notifications.

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
        errors = {}
        if self.slack_enabled:
            # Initiate the SlackNotification class
            slack = SlackNotification()

            # Craft a cloud message with slack
            blocks = slack.craft_cloud_msg(launch_time, project_name, end_date, cloud_provider, vps_name, ip_address, tags)

            # Send the message to slack
            slack_errors = slack.send_msg(message=message,channel=slack_channel, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(slack_errors)
        if self.teams_enabled:
            # Initiate the TeamsNotification class
            teams = TeamsNotification()

            # Craft a cloud message with teams
            blocks = teams.craft_cloud_msg(launch_time, project_name, end_date, cloud_provider, vps_name, ip_address, tags)

            # Send the message to teams
            teams_errors = teams.send_msg(message=message, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(teams_errors)

        return errors

    def send_unknown_asset_msg(
        self,
        launch_time: str,
        cloud_provider: str,
        vps_name: str,
        ip_address: Union[str, list],
        tags: str,
        message: str,
        slack_channel: str = None,
    ) -> dict:
        """
        Create the blocks for a nicely formatted Slack or Teams message for unknown cloud asset notifications.


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
        errors = {}
        if self.slack_enabled:
            # Initiate the SlackNotification class
            slack = SlackNotification()

            # Craft a unknown asset message with slack
            blocks = slack.craft_unknown_asset_msg(launch_time, cloud_provider, vps_name, ip_address, tags)

            # Send the message to slack
            slack_errors = slack.send_msg(message=message,channel=slack_channel, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(slack_errors)
        if self.teams_enabled:
            # Initiate the TeamsNotification class
            teams = TeamsNotification()

            # Craft a cloud message with teams
            blocks = teams.craft_unknown_asset_msg(launch_time, cloud_provider, vps_name, ip_address, tags)

            # Send the message to teams
            teams_errors = teams.send_msg(message=message, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(teams_errors)

        return errors

    def send_burned_msg(
        self,
        domain: str,
        categories: str,
        burned_explanation: str,
        message: str,
        slack_channel: str = None,
    ) -> dict:
        """
        Create the blocks for a nicely formatted Slack or Teams message for burned domain notifications.

        **Parameters**

        ``domain``
            Name of the burned domain
        ``categories``
            Categories associated with the domain
        ``burned_explanation``
            Explanation of why the domain was burned
        """
        errors = {}
        if self.slack_enabled:
            # Initiate the SlackNotification class
            slack = SlackNotification()

            # Craft a burned message with slack
            blocks = slack.craft_burned_msg(domain, categories, burned_explanation)

            # Send the message to slack
            slack_errors = slack.send_msg(message=message,channel=slack_channel, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(slack_errors)
        if self.teams_enabled:
            # Initiate the TeamsNotification class
            teams = TeamsNotification()

            # Craft a burned message with teams
            blocks = teams.craft_burned_msg(domain, categories, burned_explanation)

            # Send the message to teams
            teams_errors = teams.send_msg(message=message, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(teams_errors)

        return errors

    def send_warning_msg(
        self,
        domain: str,
        warning_type: str,
        warnings: str,
        message: str,
        slack_channel: str = None,
    ) -> dict:
        """
        Create the blocks for a nicely formatted Slack or Teams message for domain warning notifications.

        **Parameters**

        ``domain``
            Name of the domain
        ``warning_type``
            Type of warning
        ``warnings``
            Explanation of the warning
        """
        errors = {}
        if self.slack_enabled:
            # Initiate the SlackNotification class
            slack = SlackNotification()

            # Craft a warning message with slack
            blocks = slack.craft_warning_msg(domain, warning_type, warnings)

            # Send the message to slack
            slack_errors = slack.send_msg(message=message,channel=slack_channel, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(slack_errors)
        if self.teams_enabled:
            # Initiate the TeamsNotification class
            teams = TeamsNotification()

            # Craft a warning message with teams
            blocks = teams.craft_warning_msg(domain, warning_type, warnings)

            # Send the message to teams
            teams_errors = teams.send_msg(message=message, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(teams_errors)

        return errors

    def send_inactive_log_msg(
        self, oplog: str, project: str, hours_inactive: int, message: str, last_entry_date: str = None, slack_channel: str = None,
    ) -> dict:
        """
        Create the blocks for a nicely formatted Slack or Teams message for inactive oplog notifications.

        **Parameters**

        ``oplog``
            Name of the oplog
        ``project``
            Name of the project associated with the oplog
        ``last_entry_date``
            Date of the last entry in the oplog
        """
        errors = {}
        if self.slack_enabled:
            # Initiate the SlackNotification class
            slack = SlackNotification()

            # Craft a inactive log message with slack
            blocks = slack.craft_inactive_log_msg(oplog, project, hours_inactive, last_entry_date)

            # Send the message to slack
            slack_errors = slack.send_msg(message=message,channel=slack_channel, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(slack_errors)
        if self.teams_enabled:
            # Initiate the TeamsNotification class
            teams = TeamsNotification()

            # Craft a inactive log message with teams
            blocks = teams.craft_inactive_log_msg(oplog, project, hours_inactive, last_entry_date)

            # Send the message to teams
            teams_errors = teams.send_msg(message=message, blocks=blocks,)

            # Update the collective dictionary with errors
            errors.update(teams_errors)

        return errors


def send_complete_msg(self, task: Task) -> None:
    """
    Send a basic Slack or Teams message using the global Slack or Teams configuration upon completion
    of an :model:`django_q.Task`.

    **Parameters**

    ``task``
        Instance of :model:`django_q.Task`
    """
    if self.slack_enabled:
        # Initiate the SlackNotification class
        slack = SlackNotification()

        # Send the message to slack
        slack.send_slack_complete_msg(task,)
    if self.teams_enabled:
        # Initiate the TeamsNotification class
        teams = TeamsNotification()

        # Send the message to teams
        teams.send_teams_complete_msg(task,)
