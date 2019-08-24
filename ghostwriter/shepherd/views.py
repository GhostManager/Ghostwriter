"""This contains all of the views for the Shepherd application's various
webpages.
"""

# Import logging functionality
import logging

# Django imports for generic views and template rendering
from django.views import generic
from django.shortcuts import render
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Django imports for verifying a user is logged-in to access a view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

# Django imports for forms
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

# Django Q imports for task management
from django_q.tasks import async_task

# Import for references to Django's settings.py
from django.conf import settings

# Import the Shepherd application's models
from django.db.models import Q
from django.urls import reverse
# from rolodex.models import Project
from django_q.models import Task
from .forms import (CheckoutForm, DomainCreateForm,
                            DomainNoteCreateForm, BurnForm,
                            ServerNoteCreateForm, ServerCreateForm,
                            ServerCheckoutForm, TransientServerCreateForm,
                            DomainLinkForm)
from .models import (Domain, HealthStatus, DomainStatus, WhoisStatus,
                             History, DomainServerConnection, DomainNote)
from .models import (ServerNote, ServerHistory, ServerProvider,
                             ServerStatus, StaticServer, TransientServer)
from ghostwriter.rolodex.models import Project

# Import model filters for views
from .filters import DomainFilter, ServerFilter

# Import Python libraries for various things
import csv
import datetime
from io import StringIO


# Setup logger
logger = logging.getLogger(__name__)


##################
# View Functions #
##################


@login_required
def index(request):
    """View function to redirect empty requests to the dashboard."""
    return HttpResponseRedirect(reverse('home:dashboard'))


@login_required
def domain_list(request):
    """View showing all domain names. This view defaults to the
    domain_list.html template and allows for filtering.
    """
    # Check if a search parameter is in the request
    try:
        search_term = request.GET.get('domain_search')
    except Exception:
        search_term = ''
    # If there is a search term, filter the query by domain name or category
    if search_term:
        messages.success(
            request,
            'Showing search results for: %s' %
            search_term, extra_tags='alert-success')
        domains_list = Domain.objects.select_related(
                            'domain_status', 'whois_status', 'health_status'
                        ).filter(
                            Q(name__icontains=search_term) |
                            Q(all_cat__icontains=search_term)
                        ).order_by('name')
    else:
        domains_list = Domain.objects.select_related(
                            'domain_status', 'whois_status', 'health_status'
                        ).all()
    domains_filter = DomainFilter(request.GET, queryset=domains_list)
    return render(
        request,
        'shepherd/domain_list.html',
        {'filter': domains_filter})


@login_required
def server_list(request):
    """View showing all servers. This view defaults to the server_list.html
    template and allows for filtering.
    """
    servers_list = StaticServer.objects.select_related('server_status').\
        all().order_by('ip_address')
    servers_filter = ServerFilter(request.GET, queryset=servers_list)
    return render(
        request,
        'shepherd/server_list.html',
        {'filter': servers_filter})


@login_required
def ajax_load_projects(request):
    """View function used with AJAX for filtering project dropdown lists based
    on changes to a client dropdown list.
    """
    client_id = request.GET.get('client')
    projects = Project.objects.filter(client_id=client_id).order_by('codename')
    return render(
        request,
        'shepherd/project_dropdown_list.html',
        {'projects': projects})


@login_required
def domain_release(request, pk):
    """View function for releasing a domain back to the pool. The Primary Key
    passed to this view is used to look-up the requested domain.
    """
    # Fetch the checkout for the provided primary key
    checkout_instance = get_object_or_404(History, pk=pk)
    # If this is a GET request then check if domain can be released
    if request.method == 'GET':
        # Allow the action if the current user is the one who checked out
        # the domain
        if request.user == checkout_instance.operator:
            # Reset domain status to `Available` and commit the change
            domain_instance = Domain.objects.\
                get(pk=checkout_instance.domain.id)
            domain_instance.domain_status = DomainStatus.objects.\
                get(domain_status='Available')
            domain_instance.save()
            # Get the most recent project for this domain and update the
            # release date
            checkout_instance.end_date = datetime.datetime.now()
            checkout_instance.save()
            # Redirect to the user's checked-out domains
            messages.success(
                request,
                'Domain successfully released back into the pool.',
                extra_tags='alert-success')
            return HttpResponseRedirect(reverse('shepherd:user_assets'))
        # Otherwise return an error message
        else:
            messages.error(
                request,
                'Your user account does match the user that has checked out '
                'this domain, so you are not authorized to release it.',
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('shepherd:user_assets'))
    # If this is a POST (or any other method) redirect
    else:
        return HttpResponseRedirect(reverse('shepherd:user_assets'))


@login_required
def server_release(request, pk):
    """View function for releasing a server back to the pool. The Primary Key
    passed to this view is used to look-up the requested server.
    """
    # Fetch the checkout for the provided primary key
    checkout_instance = get_object_or_404(ServerHistory, pk=pk)
    # If this is a GET request then check if server can be released
    if request.method == 'GET':
        # Allow the action if the current user is the one who checked out
        # the server
        if request.user == checkout_instance.operator:
            # Reset domain status to `Available` and commit the change
            server_instance = get_object_or_404(
                StaticServer,
                pk=checkout_instance.server.id)
            server_instance.server_status = ServerStatus.objects.get(
                server_status='Available')
            server_instance.save()
            # Get the most recent project for this domain and update
            # the release date
            checkout_instance.end_date = datetime.datetime.now()
            checkout_instance.save()
            # Redirect to the user's checked-out domains
            messages.success(
                request,
                'Server successfully released back into the pool.',
                extra_tags='alert-success')
            return HttpResponseRedirect(reverse('shepherd:user_assets'))
        # Otherwise return an error message
        else:
            messages.error(
                request,
                'Your user account does match the user that has checked out '
                'this server, so you are not authorized to release it.',
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('shepherd:user_assets'))
    # If this is a POST (or any other method) redirect
    else:
        return HttpResponseRedirect(reverse('shepherd:user_assets'))


@login_required
def user_assets(request):
    """View function for displaying domains and servers checked-out for the
    current user.
    """
    # Fetch the domain and server history for the current user
    domains = History.objects.select_related(
                    'domain', 'domain__domain_status', 'project',
                    'activity_type'
                ).filter(
                    operator=request.user,
                    domain__domain_status__domain_status='Unavailable',
                    end_date__gte=datetime.datetime.now() -
                    datetime.timedelta(days=1)
                ).order_by('end_date')
    servers = ServerHistory.objects.select_related(
                    'server', 'server__server_status', 'project',
                    'server_role', 'activity_type'
                ).filter(
                    operator=request.user,
                    server__server_status__server_status='Unavailable',
                    end_date__gte=datetime.datetime.now() -
                    datetime.timedelta(days=1)
                ).order_by('end_date')
    # Pass the context on to the custom HTML
    context = {
                'domains': domains,
                'servers': servers
                }
    return render(request, 'shepherd/checkouts_for_user.html', context)


@login_required
def burn(request, pk):
    """View function for burning a domain. The Primary Key passed to this view
    is used to look-up the requested domain.
    """
    # Fetch the domain for the provided primary key
    domain_instance = get_object_or_404(Domain, pk=pk)
    # If this is a POST request then process the form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request
        form = BurnForm(request.POST)
        # Check if the form is valid
        if form.is_valid():
            # Update the domain status and commit it
            domain_instance.domain_status = DomainStatus.objects.get(
                domain_status='Burned')
            domain_instance.health_status = HealthStatus.objects.get(
                health_status='Burned')
            domain_instance.burned_explanation = form.cleaned_data[
                'burned_explanation']
            domain_instance.last_used_by = request.user
            domain_instance.save()
            # Redirect to the user's checked-out domains
            messages.warning(
                request,
                'Domain successfully marked as burned.',
                extra_tags='alert-warning')
            return HttpResponseRedirect(reverse(
                'shepherd:domain_detail',
                kwargs={'pk': pk}))
    # If this is a GET (or any other method) create the default form
    else:
        form = BurnForm()
    # Prepare the context for the checkout form
    context = {
                'form': form,
                'domain_instance': domain_instance,
                'domain_name': domain_instance.name
               }
    # Render the checkout form page
    return render(request, 'shepherd/burn.html', context)


@login_required
def import_domains(request):
    """View function for uploading and processing csv files for importing
    domain names.
    """
    # If the request is 'GET' return the upload page
    if request.method == 'GET':
        return render(request, 'shepherd/domain_import.html')
    # If not a GET, then proceed
    try:
        # Get the `csv_file` from the POSTed form data
        csv_file = request.FILES['csv_file']
        # Do a lame/basic check to see if this is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(
                request,
                'Your file is not a csv!',
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('shepherd:domain_import'))
        # The file is loaded into memory, so this view must be aware of
        # system limits
        if csv_file.multiple_chunks():
            messages.error(
                request,
                'Uploaded file is too big (%.2f MB).' %
                (csv_file.size/(1000*1000)),
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('shepherd:domain_import'))
    except Exception as e:
        messages.error(
            request, 'Unable to upload/read file: ' + repr(e),
            extra_tags='alert-danger')
        logging.getLogger('error_logger').error(
            'Unable to upload/read file. ' + repr(e))
    # Loop over the lines and save the domains to the Domains model
    try:
        # Try to read the file data
        csv_file_wrapper = StringIO(csv_file.read().decode('utf-8'))
        csv_reader = csv.DictReader(csv_file_wrapper, delimiter=',')
    except Exception as e:
        messages.error(
            request,
            'Unable to parse file: ' + repr(e),
            extra_tags='alert-danger')
        logging.getLogger('error_logger').error(
            'Unable to parse file. ' + repr(e))
        return HttpResponseRedirect(reverse('shepherd:domain_import'))
    try:
        # Process each csv row and commit it to the database
        for entry in csv_reader:
            logging.getLogger('error_logger').info(
                'Adding %s to the database', entry['name'])
            # Format dates into the format Django expects them, YYYY-MM-DD
            health_status = HealthStatus.objects.get(
                health_status__iexact=entry['health_status'])
            entry['health_status'] = health_status
            try:
                whois_status = WhoisStatus.objects.get(
                    whois_status__iexact=entry['whois_status'])
            except Exception:
                whois_status = WhoisStatus.objects.get(whois_status='Enabled')
            entry['whois_status'] = whois_status
            # Check if the optional note field is in the csv and add it as
            # NULL if not
            if 'note' not in entry:
                entry['note'] = None
            # Check if the domain_status Foreign Key is in the csv and try to
            # resolve the status
            if 'domain_status' in entry:
                try:
                    domain_status = DomainStatus.objects.get(
                        domain_status__iexact=entry['domain_status'])
                except Exception:
                    domain_status = DomainStatus.objects.get(
                        domain_status='Available')
                entry['domain_status'] = domain_status
            else:
                domain_status = DomainStatus.objects.get(
                    domain_status='Available')
                entry['domain_status'] = domain_status
            # The last_used_by field will only be set by Shepherd at check-out
            if 'last_used_by' in entry:
                entry['last_used_by'] = None
            else:
                entry['last_used_by'] = None
            # Try to pass the dict object to the `Domain` model
            try:
                # First, check if a domain with this name exists
                try:
                    instance = Domain.objects.get(name=entry['name'])
                except Domain.DoesNotExist:
                    instance = False
                if instance:
                    # This domain already exists so update that entry
                    for attr, value in entry.items():
                        setattr(instance, attr, value)
                    instance.save()
                else:
                    # This is a new domain so create it
                    new_domain = Domain(**entry)
                    new_domain.save()
            # If there is an error, store as string and then display
            except Exception as e:
                messages.error(
                    request,
                    'Failed parsing %s: %s' % (entry['name'], e),
                    extra_tags='alert-danger')
                logging.getLogger('error_logger').error(repr(e))
                pass
    except Exception as e:
        messages.error(
            request,
            'Unable to read rows: ' + repr(e),
            extra_tags='alert-danger')
        logging.getLogger('error_logger').error(
            'Unable to read rows. ' + repr(e))
    return HttpResponseRedirect(reverse('shepherd:domain_import'))


@login_required
def import_servers(request):
    """View function for uploading and processing csv files for importing
    servers.
    """
    # If the request is 'GET' return the upload page
    if request.method == 'GET':
        return render(request, 'shepherd/server_import.html')
    # If not a GET, then proceed
    try:
        # Get the `csv_file` from the POSTed form data
        csv_file = request.FILES['csv_file']
        # Do a lame/basic check to see if this is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(
                request,
                'Your file is not a csv!',
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('shepherd:server_import'))
        # The file is loaded into memory, so this view must be aware of
        # system limits
        if csv_file.multiple_chunks():
            messages.error(
                request,
                'Uploaded file is too big (%.2f MB).' %
                (csv_file.size/(1000*1000)),
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('shepherd:server_import'))
    except Exception as e:
        messages.error(
            request,
            'Unable to upload/read file: ' + repr(e),
            extra_tags='alert-danger')
        logging.getLogger('error_logger').error(
            'Unable to upload/read file. ' + repr(e))
    # Loop over the lines and save the servers to the `StaticServer` model
    try:
        # Try to read the file data
        csv_file_wrapper = StringIO(csv_file.read().decode('utf-8'))
        csv_reader = csv.DictReader(csv_file_wrapper, delimiter=',')
    except Exception as e:
        messages.error(
            request,
            'Unable to parse file: ' + repr(e),
            extra_tags='alert-danger')
        logging.getLogger('error_logger').error(
            'Unable to parse file. ' + repr(e))
        return HttpResponseRedirect(reverse('shepherd:server_import'))
    try:
        # Process each csv row and commit it to the database
        for entry in csv_reader:
            #print(entry)
            logging.getLogger('error_logger').info(
                'Adding %s to the database',
                entry['ip_address'])
            # Check if the optional note field is in the csv and add it as
            # NULL if not
            if 'note' not in entry:
                entry['note'] = None
            # Check if the server_status Foreign Key is in the csv and try to
            # resolve the status
            if 'server_status' in entry:
                try:
                    server_status = ServerStatus.objects.get(
                        server_status__iexact=entry['server_status'])
                except Exception:
                    server_status = ServerStatus.objects.get(
                        server_status='Available')
            else:
                server_status = ServerStatus.objects.get(
                    server_status='Available')
            entry['server_status'] = server_status
            # Check if the server_status Foreign Key is in the csv and try to
            # resolve the status
            if 'server_provider' in entry:
                try:
                    server_provider = ServerProvider.objects.get(
                        server_provider__iexact=entry['server_provider'])
                    entry['server_provider'] = server_provider
                except Exception:
                    messages.error(
                        request,
                        'Failed parsing %s: the "%s" server provider does not '
                        'exist in the database' %
                        (entry['ip_address'], entry['server_provider']),
                        extra_tags='alert-danger')
                    continue
            # The last_used_by field will only be set by Shepherd at
            # server check-out
            if 'last_used_by' in entry:
                entry['last_used_by'] = None
            else:
                entry['last_used_by'] = None
            # Try to pass the dict object to the `StaticServer` model
            try:
                # First, check if a server with this address exists
                try:
                    instance = StaticServer.objects.get(
                        ip_address=entry['ip_address'])
                except StaticServer.DoesNotExist:
                    instance = False
                if instance:
                    # This server already exists so update that entry
                    for attr, value in entry.items():
                        setattr(instance, attr, value)
                    instance.save()
                else:
                    # This is a new server so create it
                    new_server = StaticServer(**entry)
                    new_server.save()
            # If there is an error, store as string and then display
            except Exception as e:
                messages.error(
                    request,
                    'Failed parsing %s: %s' % (entry['ip_address'], e),
                    extra_tags='alert-danger')
                logging.getLogger('error_logger').error(repr(e))
                pass
    except Exception as e:
        messages.error(
            request,
            'Unable to read rows: ' + repr(e),
            extra_tags='alert-danger')
        logging.getLogger('error_logger').error(
            'Unable to read rows. ' + repr(e))
    return HttpResponseRedirect(reverse('shepherd:server_import'))


@login_required
def update(request):
    """View function to display the control panel for updating domain
    information.
    """
    # Check if the request is a GET
    if request.method == 'GET':
        # Collect data for category updates
        total_domains = Domain.objects.all().count()
        try:
            sleep_time = settings.DOMAINCHECK_CONFIG['sleep_time']
            update_time = round(total_domains * sleep_time / 60, 2)
        except Exception:
            sleep_time = 20
            update_time = round(total_domains * sleep_time / 60, 2)
        try:
            # Get the latest completed task from `Domain Updates`
            queryset = Task.objects.filter(group='Domain Updates')[0]
            # Get the task's start date and time
            cat_last_update_requested = queryset.started
            # Get the task's completed time
            cat_last_result = queryset.result
            # Check if the task was flagged as successful or failed
            if queryset.success:
                cat_last_update_completed = queryset.stopped
                cat_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                cat_last_update_completed = 'Failed'
                cat_last_update_time = ''
        except Exception:
            cat_last_update_requested = 'Updates Have Not Been Run Yet'
            cat_last_update_completed = ''
            cat_last_update_time = ''
            cat_last_result = ''
        # Collect data for DNS updates
        try:
            queryset = Task.objects.filter(group='DNS Updates')[0]
            dns_last_update_requested = queryset.started
            dns_last_result = queryset.result
            if queryset.success:
                dns_last_update_completed = queryset.stopped
                dns_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                dns_last_update_completed = 'Failed'
                dns_last_update_time = ''
        except Exception:
            dns_last_update_requested = 'Updates Have Not Been Run Yet'
            dns_last_update_completed = ''
            dns_last_update_time = ''
            dns_last_result = ''
        # Collect data for Namecheap updates
        enable_namecheap = settings.NAMECHEAP_CONFIG['enable_namecheap']
        try:
            queryset = Task.objects.filter(group='Namecheap Update')[0]
            namecheap_last_update_requested = queryset.started
            namecheap_last_result = queryset.result
            if queryset.success:
                namecheap_last_update_completed = queryset.stopped
                namecheap_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                namecheap_last_update_completed = 'Failed'
                namecheap_last_update_time = ''
        except Exception:
            namecheap_last_update_requested = 'A Namecheap Update Has Not Been Run Yet'
            namecheap_last_update_completed = ''
            namecheap_last_update_time = ''
            namecheap_last_result = ''
        # Assemble context for the page
        context = {
                    'total_domains': total_domains,
                    'update_time': update_time,
                    'sleep_time': sleep_time,
                    'cat_last_update_requested': cat_last_update_requested,
                    'cat_last_update_completed': cat_last_update_completed,
                    'cat_last_update_time': cat_last_update_time,
                    'cat_last_result': cat_last_result,
                    'dns_last_update_requested': dns_last_update_requested,
                    'dns_last_update_completed': dns_last_update_completed,
                    'dns_last_update_time': dns_last_update_time,
                    'dns_last_result': dns_last_result,
                    'enable_namecheap': enable_namecheap,
                    'namecheap_last_update_requested': namecheap_last_update_requested,
                    'namecheap_last_update_completed': namecheap_last_update_completed,
                    'namecheap_last_update_time': namecheap_last_update_time,
                    'namecheap_last_result': namecheap_last_result
                }
        return render(request, 'shepherd/update.html', context=context)
    else:
        return HttpResponseRedirect(reverse('shepherd:update'))


@login_required
def update_cat(request):
    """View function to schedule a background task to update domain
    categories.
    """
    # Check if the request is a POST and proceed with the task
    if request.method == 'POST':
        # Add an async task grouped as `Domain Updates`
        try:
            task_id = async_task(
                'ghostwriter.shepherd.tasks.check_domains',
                group='Domain Updates',
                hook='ghostwriter.shepherd.tasks.send_slack_complete_msg')
            messages.success(
                request,
                'Domain category update task (Task ID {}) has been '
                'successfully queued.'.
                format(task_id),
                extra_tags='alert-success')
        except Exception:
            messages.error(
                request,
                'Domain category update task could not be queued. Is the AMQP '
                'server running?',
                extra_tags='alert-danger')
    return HttpResponseRedirect(reverse('shepherd:update'))


@login_required
def update_cat_single(request, pk):
    """View function to schedule a background task to update one domain's
    categories.
    """
    # Check if the request is a POST and proceed with the task
    if request.method == 'GET':
        # Add an async task grouped as `Domain Updates`
        try:
            virustotal_api_key = settings.DOMAINCHECK_CONFIG[
                'virustotal_api_key']
        except Exception:
            virustotal_api_key = None
        try:
            task_id = async_task(
                'ghostwriter.shepherd.tasks.check_domains',
                domain=pk,
                group='Domain Updates',
                hook='ghostwriter.shepherd.tasks.send_slack_complete_msg')
            if virustotal_api_key:
                messages.success(
                    request,
                    'Domain category update task (Task ID {}) has been '
                    'successfully queued. Refresh this page in a few minutes.'.
                    format(task_id),
                    extra_tags='alert-success')
            else:
                messages.success(
                    request,
                    'Domain category update task (Task ID {}) has been '
                    'successfully queued. Refresh this page in a few '
                    'minutes. A VirusTotal API key is not configured so '
                    'checks will exclude VirusTotal and passive DNS.'.
                    format(task_id),
                    extra_tags='alert-success')
        except Exception:
            messages.error(
                request,
                'Domain category update task could not be queued. '
                'Is the AMQP server running?',
                extra_tags='alert-danger')
    return HttpResponseRedirect(reverse('shepherd:domain_detail', kwargs={'pk': pk}))


@login_required
def update_dns(request):
    """View function to schedule a background task to update domain DNS
    records.
    """
    # Check if the request is a POST and proceed with the task
    if request.method == 'POST':
        # Add an async task grouped as `DNS Updates`
        try:
            task_id = async_task(
                'ghostwriter.shepherd.tasks.update_dns',
                group='DNS Updates',
                hook='ghostwriter.shepherd.tasks.send_slack_complete_msg')
            messages.success(
                request,
                'DNS update task (Task ID {}) has been successfully queued.'.
                format(task_id),
                extra_tags='alert-success')
        except Exception:
            messages.error(
                request,
                'DNS update task could not be queued. '
                'Is the AMQP server running?',
                extra_tags='alert-danger')
    return HttpResponseRedirect(reverse('shepherd:update'))


@login_required
def update_dns_single(request, pk):
    """View function to schedule a background task to update one domain's DNS
    records.
    """
    # Check if the request is a POST and proceed with the task
    if request.method == 'GET':
        # Add an async task grouped as `DNS Updates`
        try:
            task_id = async_task(
                'ghostwriter.shepherd.tasks.update_dns',
                domain=pk,
                group='DNS Updates',
                hook='ghostwriter.shepherd.tasks.send_slack_complete_msg')
            messages.success(
                request,
                'DNS update task (Task ID {}) has been successfully queued. '
                'Refresh this page in a minute or two.'.format(task_id),
                extra_tags='alert-success')
        except Exception:
            messages.error(
                request,
                'DNS update task could not be queued. Is the AMQP server '
                'running?',
                extra_tags='alert-danger')
    return HttpResponseRedirect(reverse('shepherd:domain_detail', kwargs={'pk': pk}))


@login_required
def pull_domains_namecheap(request):
    """View function to schedule a background task to update the domain
    library from Namecheap.
    """
    # Check if the request is a POST and proceed with the task
    if request.method == 'POST':
        # Add an async task grouped as `Namecheap Update`
        try:
            task_id = async_task(
                'ghostwriter.shepherd.tasks.fetch_namecheap_domains',
                group='Namecheap Update')
            messages.success(
                request,
                'Namecheap update task (Task ID {}) has been successfully queued.'.
                format(task_id),
                extra_tags='alert-success')
        except Exception:
            messages.error(
                request,
                'Namecheap update task could not be queued. '
                'Is the AMQP server running?',
                extra_tags='alert-danger')
    return HttpResponseRedirect(reverse('shepherd:update'))


################
# View Classes #
################


class GraveyardListView(LoginRequiredMixin, generic.ListView):
    """View showing only burned and retired domains. This view calls the
    graveyard.html template.
    """
    model = Domain
    template_name = 'shepherd/graveyard.html'
    paginate_by = 100

    def get_queryset(self):
        """Customize the queryset based on search."""
        queryset = super(GraveyardListView, self).get_queryset()
        return queryset.select_related('domain_status', 'whois_status',
                                       'health_status').\
            filter(Q(domain_status__domain_status='Burned') |
                   Q(health_status__health_status='Burned')).order_by('name')


class DomainDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified domain. This view defaults
    to the domain_detail.html template.
    """
    model = Domain


class HistoryCreate(LoginRequiredMixin, CreateView):
    """View for creating new project history entries. This view defaults to
    the checkout.html template.
    """
    model = History
    form_class = CheckoutForm
    template_name = 'shepherd/checkout.html'

    def get_initial(self):
        """Set the initial values for the form."""
        self.domain = get_object_or_404(Domain, pk=self.kwargs.get('pk'))
        return {
                'domain': self.domain,
                'operator': self.request.user,
               }

    def form_valid(self, form):
        """Override form_valid to perform additional actions on new entries."""
        # Update the domain status and commit it
        domain_instance = get_object_or_404(Domain, pk=self.kwargs.get('pk'))
        domain_instance.last_used_by = self.request.user
        domain_instance.domain_status = DomainStatus.objects.get(
            domain_status='Unavailable')
        domain_instance.save()
        return super().form_valid(form)

    def get_success_url(self):
        """Override the function to return to the domain after creation."""
        messages.success(
            self.request,
            'Domain successfully checked-out.',
            extra_tags='alert-success')
        return reverse('shepherd:user_assets')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(HistoryCreate, self).get_context_data(**kwargs)
        ctx['domain_name'] = self.domain.name.upper()
        return ctx


class HistoryUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing project history entries. This view defaults
    to the checkout.html template.
    """
    model = History
    form_class = CheckoutForm
    template_name = 'shepherd/checkout.html'

    def get_success_url(self):
        """Override the function to return to the domain after update."""
        messages.success(
            self.request,
            'Domain history successfully updated.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(HistoryUpdate, self).get_context_data(**kwargs)
        ctx['domain_name'] = self.object.domain.name.upper()
        return ctx


class HistoryDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing project history entries. This view defaults
    to the confirm_delete.html template.
    """
    model = History
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('shepherd:domains')

    def get_success_url(self):
        """Override the function to return to the domain after deletion."""
        messages.warning(
            self.request,
            'Project history successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(HistoryDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'domain checkout'
        ctx['object_to_be_deleted'] = queryset
        return ctx


class DomainCreate(LoginRequiredMixin, CreateView):
    """View for creating new domain name entries. This view defaults to the
    domain_form.html template.
    """
    model = Domain
    form_class = DomainCreateForm

    def get_success_url(self):
        """Override the function to show the new domain after creation."""
        messages.success(
            self.request,
            'Domain successfully created.',
            extra_tags='alert-success')
        return reverse('shepherd:domain_detail', kwargs={'pk': self.object.pk})


class DomainUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing domain name entries. This view defaults to the
    domain_form.html template.
    """
    model = Domain
    fields = '__all__'

    def get_success_url(self):
        """Override the function to return to the domain after update."""
        messages.success(
            self.request,
            'Domain successfully updated.',
            extra_tags='alert-success')
        return reverse('shepherd:domain_detail', kwargs={'pk': self.object.id})


class DomainDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing domain name entries. This view defaults to
    the confirm_delete.html template.
    """
    model = Domain
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the domain list after
        deletion.
        """
        messages.warning(
            self.request,
            'Domain successfully deleted.',
            extra_tags='alert-warning')
        return reverse('shepherd:domains')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(DomainDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'domain'
        ctx['object_to_be_deleted'] = queryset.name.upper()
        return ctx


class ServerDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified server. This view defaults to the
    server_detail.html template.
    """
    model = StaticServer
    template_name = 'shepherd/server_detail.html'


class ServerCreate(LoginRequiredMixin, CreateView):
    """View for creating new server entries. This view defaults to the
    server_form.html template.
    """
    model = StaticServer
    template_name = 'shepherd/server_form.html'
    form_class = ServerCreateForm

    def get_success_url(self):
        """Override the function to show the new server after creation."""
        messages.success(
            self.request,
            'Server successfully created.',
            extra_tags='alert-success')
        return reverse('shepherd:server_detail', kwargs={'pk': self.object.pk})


class ServerUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing server entries. This view defaults to the
    server_form.html template.
    """
    model = StaticServer
    template_name = 'shepherd/server_form.html'
    fields = '__all__'

    def get_success_url(self):
        """Override the function to return to the server after update."""
        messages.success(
            self.request,
            'Server successfully updated.',
            extra_tags='alert-success')
        return reverse('shepherd:server_detail', kwargs={'pk': self.object.id})


class ServerDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing server entries. This view defaults to the
    confirm_delete.html template.
    """
    model = StaticServer
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the server list after
        deletion.
        """
        messages.warning(
            self.request,
            'Server successfully deleted.',
            extra_tags='alert-warning')
        return reverse('shepherd:servers')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ServerDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'static server'
        ctx['object_to_be_deleted'] = queryset.ip_address
        return ctx


class ServerHistoryCreate(LoginRequiredMixin, CreateView):
    """View for creating new server history entries. This view defaults to the
    server_checkout.html template.
    """
    model = ServerHistory
    form_class = ServerCheckoutForm
    template_name = 'shepherd/server_checkout.html'

    def get_initial(self):
        """Set the initial values for the form."""
        self.server = get_object_or_404(StaticServer, pk=self.kwargs.get('pk'))
        return {
                'server': self.server,
                'operator': self.request.user,
               }

    def form_valid(self, form):
        """Override form_valid to perform additional actions on new entries."""
        # Update the domain status and commit it
        server_instance = get_object_or_404(
            StaticServer, pk=self.kwargs.get('pk'))
        server_instance.last_used_by = self.request.user
        server_instance.server_status = ServerStatus.objects.get(
            server_status='Unavailable')
        server_instance.save()
        return super().form_valid(form)

    def get_success_url(self):
        """Override the function to return to the domain after creation."""
        messages.success(
            self.request,
            'Server successfully checked-out.',
            extra_tags='alert-success')
        return reverse('shepherd:user_assets')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ServerHistoryCreate, self).get_context_data(**kwargs)
        ctx['server_name'] = self.server.ip_address
        return ctx


class ServerHistoryUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing server history entries. This view defaults
    to the server_checkout.html template.
    """
    model = ServerHistory
    form_class = ServerCheckoutForm
    template_name = 'shepherd/server_checkout.html'

    def get_success_url(self):
        """Override the function to return to the domain after update."""
        messages.success(
            self.request,
            'Server history successfully updated.',
            extra_tags='alert-success')
        return reverse('shepherd:project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ServerHistoryUpdate, self).get_context_data(**kwargs)
        ctx['server_name'] = self.object.server.ip_address
        return ctx


class ServerHistoryDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing server history entries. This view defaults
    to the confirm_delete.html template.
    """
    model = ServerHistory
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('shepherd:domains')

    def get_success_url(self):
        """Override the function to return to the domain after deletion."""
        messages.warning(
            self.request,
            'Server history successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ServerHistoryDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'server checkout'
        ctx['object_to_be_deleted'] = queryset
        return ctx


class TransientServerCreate(LoginRequiredMixin, CreateView):
    """View for creating new VPS entries. This view defaults to the
    vps_form.html template.
    """
    model = TransientServer
    form_class = TransientServerCreateForm
    template_name = 'shepherd/vps_form.html'

    def get_success_url(self):
        """Override the function to show the project after server creation."""
        messages.success(
            self.request,
            'Server successfully added to the project.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_initial(self):
        """Set the initial values for the form."""
        self.project_instance = get_object_or_404(
            Project, pk=self.kwargs.get('pk'))
        return {
                'project': self.project_instance,
                'operator': self.request.user
               }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(TransientServerCreate, self).get_context_data(**kwargs)
        ctx['project_name'] = self.project_instance.codename
        return ctx


class TransientServerUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing VPS entries. This view defaults to the
    vps_form.html template.
    """
    model = TransientServer
    form_class = TransientServerCreateForm
    template_name = 'shepherd/vps_form.html'

    def get_success_url(self):
        """Override the function to show the project after server creation."""
        messages.success(
            self.request,
            'Server information successfully updated.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})


class TransientServerDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing VPS entries. This view defaults to the
    confirm_delete.html template.
    """
    model = TransientServer
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to show the project after server creation."""
        messages.success(
            self.request,
            'Server successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(TransientServerDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'virtual private server'
        ctx['object_to_be_deleted'] = queryset.ip_address
        return ctx


class DomainServerConnectionCreate(LoginRequiredMixin, CreateView):
    """View for creating new DNS connections. This view defaults to the
    connect_form.html template.
    """
    model = DomainServerConnection
    form_class = DomainLinkForm
    template_name = 'shepherd/connect_form.html'

    def get_success_url(self):
        """Override the function to show the project after server creation."""
        messages.success(
            self.request,
            'Server successfully associated with domain.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_form_kwargs(self, **kwargs):
        """Set the kwarg for the form so querysets can be filtered."""
        form_kwargs = super(
            DomainServerConnectionCreate, self).get_form_kwargs(**kwargs)
        form_kwargs['project'] = self.project_instance
        return form_kwargs

    def get_initial(self):
        """Set the initial values for the form."""
        self.project_instance = get_object_or_404(
            Project, pk=self.kwargs.get('pk'))
        return {
                'project': self.project_instance
               }


class DomainServerConnectionUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing DNS connections. This view defaults to the
    connect_form.html template.
    """
    model = DomainServerConnection
    form_class = DomainLinkForm
    template_name = 'shepherd/connect_form.html'

    def get_success_url(self):
        """Override the function to show the project after server creation."""
        messages.success(
            self.request,
            'Connection information successfully updated.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_form_kwargs(self, **kwargs):
        """Set the kwarg for the form so querysets can be filtered."""
        form_kwargs = super(
            DomainServerConnectionUpdate, self).get_form_kwargs(**kwargs)
        form_kwargs['project'] = self.object.project
        return form_kwargs


class DomainServerConnectionDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing DNS connections. This view defaults to the
    confirm_delete.html template.
    """
    model = DomainServerConnection
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to show the project after server creation."""
        messages.success(
            self.request,
            'Domain and server connection successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(
            DomainServerConnectionDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'domain + server association'
        if queryset.static_server:
            ctx['object_to_be_deleted'] = '{} « » {}'.format(
                queryset.domain.domain.name,
                queryset.static_server.server.ip_address)
        elif queryset.transient_server:
            ctx['object_to_be_deleted'] = '{} « » {}'.format(
                queryset.domain.domain.name,
                queryset.transient_server.ip_address)
        else:
            ctx['object_to_be_deleted'] = 'The Impossible Has Happened'
        return ctx


class DomainNoteCreate(LoginRequiredMixin, CreateView):
    """View for creating new note entries. This view defaults to the
    domain_note_form.html template.
    """
    model = DomainNote
    form_class = DomainNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully added to this domain.',
            extra_tags='alert-success')
        return reverse('shepherd:domain_detail', kwargs={'pk': self.object.domain.id})

    def get_initial(self):
        """Set the initial values for the form."""
        domain_instance = get_object_or_404(Domain, pk=self.kwargs.get('pk'))
        domain = domain_instance
        return {
                'domain': domain,
                'operator': self.request.user
               }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(DomainNoteCreate, self).get_context_data(**kwargs)
        domain_instance = get_object_or_404(Domain, pk=self.kwargs.get('pk'))
        ctx['domain_name'] = domain_instance.name.upper()
        return ctx


class DomainNoteUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing note entries. This view defaults to the
    domain_note_form.html template.
    """
    model = DomainNote
    form_class = DomainNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully updated.',
            extra_tags='alert-success')
        return reverse('shepherd:domain_detail', kwargs={'pk': self.object.domain.pk})


class DomainNoteDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing note entries. This view defaults to the
    confirm_delete.html template.
    """
    model = DomainNote
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the domain after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('shepherd:domain_detail', kwargs={'pk': self.object.domain.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(DomainNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'note'
        ctx['object_to_be_deleted'] = queryset.note
        return ctx


class ServerNoteCreate(LoginRequiredMixin, CreateView):
    """View for creating new note entries. This view defaults to the
    server_note_form.html template.
    """
    model = ServerNote
    form_class = ServerNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully added to this server.',
            extra_tags='alert-success')
        return reverse('shepherd:server_detail', kwargs={'pk': self.object.server.id})

    def get_initial(self):
        """Set the initial values for the form."""
        server_instance = get_object_or_404(
            StaticServer, pk=self.kwargs.get('pk'))
        server = server_instance
        return {
                'server': server,
                'operator': self.request.user
               }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ServerNoteCreate, self).get_context_data(**kwargs)
        server_instance = get_object_or_404(
            StaticServer, pk=self.kwargs.get('pk'))
        ctx['server_name'] = server_instance.ip_address
        return ctx


class ServerNoteUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing note entries. This view defaults to the
    note_form.html template.
    """
    model = ServerNote
    form_class = ServerNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully updated.',
            extra_tags='alert-success')
        return reverse('shepherd:server_detail', kwargs={'pk': self.object.server.pk})


class ServerNoteDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing note entries. This view defaults to the
    confirm_delete.html template.
    """
    model = ServerNote
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the server after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('shepherd:server_detail', kwargs={'pk': self.object.server.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ServerNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'note'
        ctx['object_to_be_deleted'] = queryset.note
        return ctx
