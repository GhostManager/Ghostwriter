"""This contains all of the views for the Home application's various
webpages.
"""

import logging
import datetime

# Django imports for generic views and template rendering
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required

# Django imports for verifying a user is logged-in to access a view
from django.contrib.auth.decorators import login_required

# Django imports for forms
from django.http import HttpResponseRedirect

# Django Q imports for task management
from django_q.tasks import async_task

# Django imports for updating passwords
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.contrib.auth.forms import PasswordChangeForm

# Import for references to Django's settings.py
from django.conf import settings

# Import additional models
from django.db.models import Q
from django_q.models import Task
from .models import UserProfile
from .forms import UserProfileForm
# from django.contrib.auth.models import User
from ghostwriter.rolodex.models import ProjectAssignment
from ghostwriter.reporting.models import ReportFindingLink

User = get_user_model()

# Setup logger
logger = logging.getLogger(__name__)


##################
# View Functions #
##################

@login_required
def dashboard(request):
    """View function for the home page, index.html."""
    # from ghostwriter.rolodex.models import ProjectAssignment
    # from ghostwriter.reporting.models import ReportFindingLink
    recent_tasks = Task.objects.all()[:5]
    user_tasks = ReportFindingLink.objects.\
        select_related('report', 'report__project').\
        filter(Q(assigned_to=request.user) & Q(report__complete=False) &
              Q(complete=False)).order_by('report__project__end_date')[:10]
    user_projects = ProjectAssignment.objects.\
        select_related('project', 'project__client', 'role').\
        filter(Q(operator=request.user) &
              Q(start_date__lte=datetime.datetime.now()) &
              Q(end_date__gte=datetime.datetime.now()))
    upcoming_project = ProjectAssignment.objects.\
        select_related('project', 'project__client', 'role').\
        filter(Q(operator=request.user) &
              Q(start_date__gt=datetime.datetime.now()))
    # Assemble the context dictionary to pas to the dashboard
    context = {
        'user_projects': user_projects,
        'upcoming_project': upcoming_project,
        'recent_tasks': recent_tasks,
        'user_tasks': user_tasks
    }
    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


@login_required
def profile(request):
    """View function for the user profile, profile.html."""
    # Get the current user's user object
    # user = request.user
    # # Look-up the username in the database
    # current_user_name = User.objects.get(username=user.username)
    # current_user_avatar = UserProfile.objects.get(user=user.id)
    # If ths is a POST, process it as a password update
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # This is a VERY important step!
            update_session_auth_hash(request, user)
            messages.success(request,
                             'Your password was successfully updated!',
                             extra_tags='alert-success')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'home/profile.html', {
        'form': form,
        # 'current_user': current_user_name,
        # 'user_avatar': current_user_avatar
    })


@login_required
def upload_avatar(request):
    """View function to modify the user profile avatar with
    upload_avatar.html.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST,
                               request.FILES,
                               instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            return redirect('home:profile')
    else:
        form = UserProfileForm()
    return render(request, 'home/upload_avatar.html', {'form': form})


@login_required
@staff_member_required
def management(request):
    """View function to display the current settings configured for
    Ghostwriter.
    """
    # Get the *_CONFIG dictionaries from settings.py
    config = {}
    config.update(settings.SLACK_CONFIG)
    config.update(settings.NAMECHEAP_CONFIG)
    config.update(settings.DOMAINCHECK_CONFIG)
    # Pass the relevant settings to management.html
    context = {
        'timezone': settings.TIME_ZONE,
        'sleep_time': config['sleep_time'],
        'slack_emoji': config['slack_emoji'],
        'enable_slack': config['enable_slack'],
        'slack_channel': config['slack_channel'],
        'slack_username': config['slack_username'],
        'slack_webhook_url': config['slack_webhook_url'],
        'virustotal_api_key': config['virustotal_api_key'],
        'slack_alert_target': config['slack_alert_target'],
        'namecheap_client_ip': config['client_ip'],
        'enable_namecheap': config['enable_namecheap'],
        'namecheap_api_key': config['namecheap_api_key'],
        'namecheap_username': config['namecheap_username'],
        'namecheap_page_size': config['namecheap_page_size'],
        'namecheap_api_username': config['namecheap_api_username']
    }
    return render(request, 'home/management.html', context=context)


@login_required
@staff_member_required
def send_slack_test_msg(request):
    """View function to schedule a background task to send a test Slack
    message.
    """
    # Check if the request is a POST and proceed with the task
    if request.method == 'POST':
        # Add an async task grouped as `Test Slack Message`
        try:
            task_id = async_task(
                'ghostwriter.shepherd.tasks.send_slack_test_msg',
                group='Test Slack Message')
            messages.success(
                request,
                'Test Slack message has been successfully queued.',
                extra_tags='alert-success')
        except Exception:
            messages.error(
                request,
                'Test Slack message task could not be queued. '
                'Is the AMQP server running?',
                extra_tags='alert-danger')
    return HttpResponseRedirect(reverse('home:management'))
