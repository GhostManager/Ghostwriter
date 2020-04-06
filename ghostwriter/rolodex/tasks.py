"""This contains tasks to be run using Django Q and Redis."""

# Import the rolodex application's models and settings
from django.db.models import Q
from django.conf import settings

from .models import Project

# Import Python libraries for various things
import json
import requests
import datetime
from datetime import date


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


def check_project_freshness():
    """Check all incomplete projects to see if they are past due to be finished."""
    project_queryset = Project.objects.filter(complete=False)
    for project in project_queryset:
        nag_date = project.end_date + datetime.timedelta(1)
        # Check if date is before or is the end date
        if date.today() >= nag_date:
            message = '{} : This project should now be complete but is not marked as such in Ghostwriter. Extend the end date or mark the project and check that all reports have been marked as completed and delivered.'.format(project)
            if project.slack_channel:
                send_slack_msg(message, project.slack_channel)
            else:
                send_slack_msg(message)
