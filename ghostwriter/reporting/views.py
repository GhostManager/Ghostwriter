"""This contains all of the views for the Ghostwriter application's
various webpages.
"""

# Import logging functionality
import logging

# Django imports for generic views and template rendering
from django.urls import reverse
from django.views import generic
from django.core.files import File
from django.shortcuts import render
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Imports for Signals
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

# Django imports for verifying a user is logged-in to access a view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

# Django imports for forms
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404

# Import for references to Django's settings.py and storage
from django.conf import settings

# Import models and forms
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()

# from rolodex.models import Project, ProjectAssignment
from .models import (
    Finding, Severity, FindingType, Report,
    ReportFindingLink, Evidence, Archive,
    FindingNote, LocalFindingNote)
from .forms import (
    FindingCreateForm, ReportCreateForm,
    ReportFindingLinkUpdateForm, EvidenceForm,
    FindingNoteCreateForm, LocalFindingNoteCreateForm)

# Import model filters for views
from .filters import FindingFilter, ReportFilter, ArchiveFilter

# Import Python libraries for various things
import io
import os
import csv
import zipfile

# Import for generating the xlsx reports in memory
from xlsxwriter.workbook import Workbook

# Import custom modules
from modules import reportwriter


# Setup logger
logger = logging.getLogger(__name__)


#####################
# Signals Functions #
#####################

@receiver(post_init, sender=Evidence)
def backup_evidence_path(sender, instance, **kwargs):
    """Backup the old evidence file's path so it can be cleaned up after the
    new file is uploaded.
    """
    instance._current_evidence = instance.document


@receiver(post_save, sender=Evidence)
def delete_old_evidence(sender, instance, **kwargs):
    """Delete the old evidence file when it is replaced."""
    if hasattr(instance, '_current_evidence'):
        if instance._current_evidence != instance.document.path:
            try:
                os.remove(instance._current_evidence.path)
            except Exception:
                pass


##################
# View Functions #
##################


@login_required
def index(request):
    """View function to redirect empty requests to the dashboard."""
    return HttpResponseRedirect(reverse('home:dashboard'))


@login_required
def findings_list(request):
    """View showing all available findings. This view defaults to the
    finding_list.html template and allows for filtering.
    """
    # Check if a search parameter is in the request
    try:
        search_term = request.GET.get('finding_search')
    except Exception:
        search_term = ''
    if search_term:
        messages.success(request, 'Displaying search results for: %s' %
                         search_term, extra_tags='alert-success')
        findings_list = Finding.objects.\
            select_related('severity', 'finding_type').\
            filter(Q(title__icontains=search_term) |
                   Q(description__icontains=search_term)).\
            order_by('severity__weight', 'finding_type', 'title')
    else:
        findings_list = Finding.objects.\
            select_related('severity', 'finding_type').\
            all().order_by('severity__weight', 'finding_type', 'title')
    findings_filter = FindingFilter(request.GET, queryset=findings_list)
    return render(request, 'reporting/finding_list.html',
                  {'filter': findings_filter})


@login_required
def reports_list(request):
    """View showing all reports. This view defaults to the report_list.html
    template and allows for filtering.
    """
    reports_list = Report.objects.select_related('created_by').all().\
        order_by('complete', 'title')
    reports_filter = ReportFilter(request.GET, queryset=reports_list)
    return render(request, 'reporting/report_list.html',
                  {'filter': reports_filter})


@login_required
def archive_list(request):
    """View showing all archived reports. This view defaults to the
    report_list.html template and allows for filtering.
    """
    archive_list = Archive.objects.select_related('project__client').all().\
        order_by('project__client')
    archive_filter = ArchiveFilter(request.GET, queryset=archive_list)
    return render(request, 'reporting/archives.html',
                  {'filter': archive_filter})


@login_required
def import_findings(request):
    """View function for uploading and processing csv files and importing
    findings.
    """
    # If the request is 'GET' return the upload page
    if request.method == 'GET':
        return render(request, 'reporting/findings_import.html')
    # If not a GET, then proceed
    try:
        # Get the `csv_file` from the POSTed form data
        csv_file = request.FILES['csv_file']
        # Do a lame/basic check to see if this is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Your file is not a csv!',
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:import_findings'))
        # The file is loaded into memory, so we must be aware of system limits
        if csv_file.multiple_chunks():
            messages.error(request, 'Uploaded file is too big (%.2f MB).' %
                           (csv_file.size/(1000*1000)),
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:import_findings'))
    # General catch-all if something goes terribly wrong
    except Exception as e:
        messages.error(request, 'Unable to upload/read file: ' + repr(e),
                       extra_tags='alert-danger')
        logging.getLogger('error_logger').\
            error('Unable to upload/read file. ' + repr(e))
    # Loop over the lines and save the domains to the Finding model
    try:
        # Try to read the file data from memory
        csv_file_wrapper = io.StringIO(csv_file.read().decode())
        csv_reader = csv.DictReader(csv_file_wrapper, delimiter=',')
    except Exception as e:
        messages.error(request, 'Unable to parse file: ' + repr(e),
                       extra_tags='alert-danger')
        logging.getLogger('error_logger').\
            error('Unable to parse file. ' + repr(e))
        return HttpResponseRedirect(reverse('reporting:import_findings'))
    try:
        error_count = 0
        # Process each csv row and commit it to the database
        for entry in csv_reader:
            if error_count > 5:
                raise Exception("Too many errors.  Discontinuing import.")
            
            title = entry.get('title', None)
            if title is None:
                messages.error(request, 'Missing title field', extra_tags='alert-danger')
                logging.getLogger('error_logger').error('Missing title field')
                error_count += 1
                continue

            logging.getLogger('error_logger').info('Adding %s to the database',
                                                   entry['title'])
            # Create a Severity object for the provided rating (e.g. High)
            severity_entry = entry.get('severity', "Informational")
            try:
                severity = Severity.objects.get(severity__iexact=severity_entry)
            except Severity.DoesNotExist:
                severity = Severity(severity=severity_entry)
                severity.save()

            # Create a FindingType object for the provided type (e.g. Network)
            type_entry = entry.get('finding_type', 'Network')
            try:
                finding_type = FindingType.objects.get(finding_type__iexact=type_entry)
            except FindingType.DoesNotExist:
                finding_type = FindingType(finding_type=type_entry)
                finding_type.save()

            try:
                instance, created = Finding.objects.update_or_create(
                    title=entry.get('title')
                )
                for attr, value in entry.items():
                    if attr not in ['severity', 'finding_type']:
                        setattr(instance, attr, value)
                instance.severity = severity
                instance.finding_type = finding_type
                instance.save()
            except Exception as e:
                messages.error(request, 'Failed parsing %s: %s' %
                               (entry['title'], e), extra_tags='alert-danger')
                logging.getLogger('error_logger').error(repr(e))
                error_count += 1
                pass

        messages.success(request, 'Your csv file has been imported '
                         'successfully =)', extra_tags='alert-success')
    
    except Exception as e:
        messages.error(request, str(e), extra_tags='alert-danger')
        logging.getLogger('error_logger').error(repr(e))

    return HttpResponseRedirect(reverse('reporting:import_findings'))


@login_required
def assign_finding(request, pk):
    """View function for adding a finding to the user's active report."""
    def get_position(report_pk):
        position = ReportFindingLink.objects.\
            filter(report__pk=report_pk).count()
        if position:
            return position + 1
        else:
            return 1
    # The user must have the `active_report` session variable
    # Get the variable and default to `None` if it does not exist
    active_report = request.session.get('active_report', None)
    if active_report:
        try:
            report = Report.objects.get(pk=active_report['id'])
        except Exception:
            messages.error(request, 'You have no active report! Select a '
                           'report to edit before trying to edit one.',
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:findings'))
        finding = Finding.objects.get(pk=pk)
        report_link = ReportFindingLink(title=finding.title,
                                        description=finding.description,
                                        impact=finding.impact,
                                        mitigation=finding.mitigation,
                                        replication_steps=finding.
                                        replication_steps,
                                        host_detection_techniques=finding.
                                        host_detection_techniques,
                                        network_detection_techniques=finding.
                                        network_detection_techniques,
                                        references=finding.references,
                                        severity=finding.severity,
                                        finding_type=finding.finding_type,
                                        finding_guidance=finding.finding_guidance,
                                        report=report,
                                        assigned_to=request.user,
                                        position=get_position(
                                            active_report['id']))
        report_link.save()
        messages.success(request, '%s successfully added to report.' %
                         finding.title, extra_tags='alert-success')
        return HttpResponseRedirect(reverse('reporting:findings'))
    else:
        messages.error(request, 'You have no active report! Select a report '
                       'to edit before trying to edit one.',
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('reporting:findings'))


@login_required
def assign_blank_finding(request, pk):
    """View function for adding a blank finding to the specified report."""
    def get_position(report_pk):
        position = ReportFindingLink.objects.filter(report=report).count()
        if position:
            return position + 1
        else:
            return 1
    try:
        report = Report.objects.get(pk=pk)
    except Exception:
        messages.error(request, 'A valid report could not be found for this '
                       'blank finding.',
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('reporting:reports'))
    report_link = ReportFindingLink(title='Blank Template',
                                    description='',
                                    impact='',
                                    mitigation='',
                                    replication_steps='',
                                    host_detection_techniques='',
                                    network_detection_techniques='',
                                    references='',
                                    severity=Severity.objects.
                                    get(severity='Informational'),
                                    finding_type=FindingType.objects.
                                    get(finding_type='Network'),
                                    report=report,
                                    assigned_to=request.user,
                                    position=get_position(report))
    report_link.save()
    messages.success(request, 'A blank finding has been successfully added to '
                     'report.',
                     extra_tags='alert-success')
    return HttpResponseRedirect(reverse('reporting:report_detail', args=(report.id,)))


@login_required
def activate_report(request, pk):
    """View function to set the specified report as the current user's active
    report.
    """
    # Set the user's session variable
    try:
        report_instance = Report.objects.get(pk=pk)
        if report_instance:
            request.session['active_report'] = {}
            request.session['active_report']['id'] = pk
            request.session['active_report']['title'] = report_instance.title
            messages.success(request, '%s is now your active report.' %
                             report_instance.title, extra_tags='alert-success')
            return HttpResponseRedirect(reverse('reporting:report_detail', args=(pk, )))
        else:
            messages.error(request, 'The specified report does not exist!',
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:reports'))
    except Exception:
        messages.error(request, 'Could not set the requested report as your '
                       'active report.',
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('reporting:reports'))


@login_required
def report_status_toggle(request, pk):
    """View function to toggle the status for the specified report."""
    try:
        report_instance = Report.objects.get(pk=pk)
        if report_instance:
            if report_instance.complete:
                report_instance.complete = False
                report_instance.save()
                messages.success(request, '%s is now marked as incomplete.' %
                                 report_instance.title,
                                 extra_tags='alert-success')
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(pk, )))
            else:
                report_instance.complete = True
                report_instance.save()
                messages.success(request, '%s is now marked as complete.' %
                                 report_instance.title,
                                 extra_tags='alert-success')
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(pk, )))
        else:
            messages.error(request, 'The specified report does not exist!',
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:reports'))
    except Exception:
        messages.error(request, "Could not update the report's status!",
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('reporting:reports'))


@login_required
def report_delivery_toggle(request, pk):
    """View function to toggle the delivery status for the specified report."""
    try:
        report_instance = Report.objects.get(pk=pk)
        if report_instance:
            if report_instance.delivered:
                report_instance.delivered = False
                report_instance.save()
                messages.success(request, '%s is now marked as not delivered.' %
                                 report_instance.title,
                                 extra_tags='alert-success')
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(pk, )))
            else:
                report_instance.delivered = True
                report_instance.save()
                messages.success(request, '%s is now marked as delivered.' %
                                 report_instance.title,
                                 extra_tags='alert-success')
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(pk, )))
        else:
            messages.error(request, 'The specified report does not exist!',
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:reports'))
    except Exception:
        messages.error(request, "Could not update the report's status!",
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('reporting:reports'))


@login_required
def finding_status_toggle(request, pk):
    """View function to toggle the status for the specified finding."""
    try:
        finding_instance = ReportFindingLink.objects.get(pk=pk)
        if finding_instance:
            if finding_instance.complete:
                finding_instance.complete = False
                finding_instance.save()
                messages.success(request, '%s is now marked as in need of '
                                 'editing.' % finding_instance.title,
                                 extra_tags='alert-success')
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(
                                                finding_instance.report.id, )))
            else:
                finding_instance.complete = True
                finding_instance.save()
                messages.success(request, '%s is now marked as ready for '
                                 'review.' % finding_instance.title,
                                 extra_tags='alert-success')
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(
                                                finding_instance.report.id, )))
        else:
            messages.error(request, 'The specified finding does not exist!',
                           extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:reports'))
    except Exception:
        messages.error(request, 'Could not set the requested finding as '
                       'complete.',
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('reporting:reports'))


@login_required
def upload_evidence(request, pk):
    """View function for handling evidence file uploads."""
    if request.method == 'POST':
        form = EvidenceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            active_report = request.session.get('active_report', None)
            messages.success(request, 'Evidence uploaded successfully',
                             extra_tags='alert-success')
            if 'id' in active_report:
                return HttpResponseRedirect(reverse('reporting:report_detail',
                                            args=(active_report['id'],)))
            else:
                return HttpResponseRedirect(reverse('reporting:reports'))
    else:
        form = EvidenceForm(initial={
            'finding': pk,
            'uploaded_by': request.user
            })
    return render(request, 'reporting/evidence_form.html', {'form': form})


@login_required
def view_evidence(request, pk):
    """View function for viewing evidence file uploads."""
    evidence_instance = Evidence.objects.get(pk=pk)
    file_content = None
    if (
            evidence_instance.document.name.endswith('.txt') or
            evidence_instance.document.name.endswith('.log') or
            evidence_instance.document.name.endswith('.ps1') or
            evidence_instance.document.name.endswith('.py') or
            evidence_instance.document.name.endswith('.md')
      ):
        filetype = 'text'
        file_content = evidence_instance.document.read().splitlines()
    elif (
        evidence_instance.document.name.endswith('.jpg') or
        evidence_instance.document.name.endswith('.png') or
        evidence_instance.document.name.endswith('.jpeg')
      ):
        filetype = 'image'
    else:
        filetype = 'unknown'
    context = {
                'filetype': filetype,
                'evidence': evidence_instance,
                'file_content': file_content
              }
    return render(request, 'reporting/evidence_detail.html', context=context)


@login_required
def position_increase(request, pk):
    """View function to increase a finding's position which moves it down the
    list.
    """
    finding_instance = ReportFindingLink.objects.get(pk=pk)
    finding_instance.position = finding_instance.position + 1
    finding_instance.save(update_fields=['position'])
    return HttpResponseRedirect(reverse('reporting:report_detail',
                                args=(finding_instance.report.id,)))


@login_required
def position_decrease(request, pk):
    """View function to decrease a finding's position which moves it up the
    list.
    """
    finding_instance = ReportFindingLink.objects.get(pk=pk)
    finding_instance.position = finding_instance.position - 1
    finding_instance.save(update_fields=['position'])
    return HttpResponseRedirect(reverse('reporting:report_detail',
                                args=(finding_instance.report.id,)))


@login_required
def generate_docx(request, pk):
    """View function to generate a docx report for the specified report."""
    report_instance = Report.objects.get(pk=pk)
    # Ask Spenny to make us a report with these findings
    output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
    evidence_path = os.path.join(settings.MEDIA_ROOT)
    template_loc = os.path.join(settings.TEMPLATE_LOC, 'template.docx')
    spenny = reportwriter.Reportwriter(
        report_instance,
        output_path,
        evidence_path,
        template_loc)
    docx = spenny.generate_word_docx()
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.'
        'wordprocessingml.document')
    response['Content-Disposition'] = 'attachment; filename=report.docx'
    docx.save(response)
    return response


@login_required
def generate_xlsx(request, pk):
    """View function to generate a xlsx report for the specified report."""
    report_instance = Report.objects.get(pk=pk)
    # Ask Spenny to make us a report with these findings
    output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
    evidence_path = os.path.join(settings.MEDIA_ROOT)
    template_loc = None
    spenny = reportwriter.Reportwriter(
        report_instance,
        output_path,
        evidence_path,
        template_loc)
    output = io.BytesIO()
    workbook = Workbook(output, {'in_memory': True})
    spenny.generate_excel_xlsx(workbook)
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/application/vnd.openxmlformats-'
        'officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=report.xlsx'
    output.close()
    return response


@login_required
def generate_pptx(request, pk):
    """View function to generate a pptx report for the specified report."""
    report_instance = Report.objects.get(pk=pk)
    # Ask Spenny to make us a report with these findings
    output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
    evidence_path = os.path.join(settings.MEDIA_ROOT)
    template_loc = os.path.join(settings.TEMPLATE_LOC, 'template.pptx')
    spenny = reportwriter.Reportwriter(
        report_instance,
        output_path,
        evidence_path,
        template_loc)
    pptx = spenny.generate_powerpoint_pptx()
    response = HttpResponse(
        content_type='application/application/vnd.openxmlformats-'
        'officedocument.presentationml.presentation')
    response['Content-Disposition'] = 'attachment; filename=report.pptx'
    pptx.save(response)
    return response


@login_required
def generate_json(request, pk):
    """View function to generate a json report for the specified report."""
    report_instance = Report.objects.get(pk=pk)
    # Ask Spenny to make us a report with these findings
    output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
    evidence_path = os.path.join(settings.MEDIA_ROOT)
    template_loc = None
    spenny = reportwriter.Reportwriter(
        report_instance,
        output_path,
        evidence_path,
        template_loc)
    json = spenny.generate_json()
    return HttpResponse(json, 'application/json')


@login_required
def generate_all(request, pk):
    """View function to generate all report types for the specified report."""
    report_instance = Report.objects.get(pk=pk)
    docx_template_loc = os.path.join(settings.TEMPLATE_LOC, 'template.docx')
    pptx_template_loc = os.path.join(settings.TEMPLATE_LOC, 'template.pptx')
    # Ask Spenny to make us reports with these findings
    output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
    evidence_path = os.path.join(settings.MEDIA_ROOT)
    template_loc = os.path.join(
        settings.MEDIA_ROOT,
        'templates',
        'template.docx')
    spenny = reportwriter.Reportwriter(
        report_instance,
        output_path,
        evidence_path,
        template_loc)
    json_doc, word_doc, excel_doc, ppt_doc = spenny.generate_all_reports(
        docx_template_loc,
        pptx_template_loc)
    # Create a zip file in memory and add the reports to it
    zip_buffer = io.BytesIO()
    zf = zipfile.ZipFile(zip_buffer, 'a')
    zf.writestr('report.json', json_doc)
    zf.writestr('report.docx', word_doc.getvalue())
    zf.writestr('report.xlsx', excel_doc.getvalue())
    zf.writestr('report.pptx', ppt_doc.getvalue())
    zf.close()
    zip_buffer.seek(0)
    # Return the buffer in the HTTP response
    response = HttpResponse(content_type='application/x-zip-compressed')
    response['Content-Disposition'] = 'attachment; filename=reports.zip'
    response.write(zip_buffer.read())
    return response


@login_required
def zip_directory(path, zip_handler):
    """Zip the target directory and all of its contents, for archiving
    purposes.
    """
    # Walk the target directory
    abs_src = os.path.abspath(path)
    for root, dirs, files in os.walk(path):
        # Add each file to the zip file handler
        for file in files:
            absname = os.path.abspath(os.path.join(root, file))
            arcname = absname[len(abs_src) + 1:]
            zip_handler.write(os.path.join(root, file), 'evidence/' + arcname)


@login_required
def archive(request, pk):
    """View function to generate all report types for the specified report and
    then zip all reports and evidence. The archive file is saved is saved in
    the archives directory.
    """
    report_instance = Report.objects.\
        select_related('project', 'project__client').get(pk=pk)
    archive_loc = os.path.join(settings.MEDIA_ROOT, 'archives')
    evidence_loc = os.path.join(settings.MEDIA_ROOT, 'evidence', str(pk))
    docx_template_loc = os.path.join(
        settings.MEDIA_ROOT,
        'templates',
        'template.docx')
    pptx_template_loc = os.path.join(
        settings.MEDIA_ROOT,
        'templates',
        'template.pptx')
    # Ask Spenny to make us reports with these findings
    output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
    evidence_path = os.path.join(settings.MEDIA_ROOT)
    template_loc = os.path.join(
        settings.MEDIA_ROOT,
        'templates',
        'template.docx')
    spenny = reportwriter.Reportwriter(
        report_instance,
        output_path,
        evidence_path,
        template_loc)
    json_doc, word_doc, excel_doc, ppt_doc = spenny.generate_all_reports(
        docx_template_loc,
        pptx_template_loc)
    # Create a zip file in memory and add the reports to it
    zip_buffer = io.BytesIO()
    zf = zipfile.ZipFile(zip_buffer, 'a')
    zf.writestr('report.json', json_doc)
    zf.writestr('report.docx', word_doc.getvalue())
    zf.writestr('report.xlsx', excel_doc.getvalue())
    zf.writestr('report.pptx', ppt_doc.getvalue())
    zip_directory(evidence_loc, zf)
    zf.close()
    zip_buffer.seek(0)
    with open(os.path.join(
        archive_loc,
        report_instance.title + '.zip'),
      'wb') as archive_file:
        archive_file.write(zip_buffer.read())
        new_archive = Archive(
            client=report_instance.project.client,
            report_archive=File(open(os.path.join(
                archive_loc,
                report_instance.title + '.zip'), 'rb')))
    new_archive.save()
    messages.success(request, '%s has been archived successfully.' %
                     report_instance.title, extra_tags='alert-success')
    return HttpResponseRedirect(reverse('reporting:archived_reports'))


@login_required
def download_archive(request, pk):
    """View function to allow for downloading archived reports."""
    archive_instance = Archive.objects.get(pk=pk)
    file_path = os.path.join(
        settings.MEDIA_ROOT,
        archive_instance.report_archive.path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as archive:
            response = HttpResponse(
                archive.read(),
                content_type='application/x-zip-compressed')
            response['Content-Disposition'] = \
                'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404


@login_required
def clone_report(request, pk):
    """View function to clone the specified report along with all of its
    findings.
    """
    report_instance = ReportFindingLink.objects.\
        select_related('report').filter(report=pk)
    # Clone the report by editing title, setting PK to `None`, and saving it
    report_to_clone = report_instance[0].report
    report_to_clone.title = report_to_clone.title + ' Copy'
    report_to_clone.complete = False
    report_to_clone.pk = None
    report_to_clone.save()
    new_report_pk = report_to_clone.pk
    for finding in report_instance:
        finding.report = report_to_clone
        finding.pk = None
        finding.save()
    return HttpResponseRedirect(reverse(
        'reporting:report_detail',
        kwargs={'pk': new_report_pk}))


@login_required
def convert_finding(request, pk):
    """View function to convert a finding in a report to a master finding
    for the library.
    """
    finding_instance = ReportFindingLink.objects.get(pk=pk)
    new_finding = Finding(
        title=finding_instance.title,
        description=finding_instance.description,
        impact=finding_instance.impact,
        mitigation=finding_instance.mitigation,
        replication_steps=finding_instance.replication_steps,
        host_detection_techniques=finding_instance.host_detection_techniques,
        network_detection_techniques=finding_instance.network_detection_techniques,
        references=finding_instance.references,
        severity=finding_instance.severity,
        finding_type=finding_instance.finding_type
    )
    new_finding.save()
    new_finding_pk = new_finding.pk
    return HttpResponseRedirect(reverse(
        'reporting:finding_detail',
        kwargs={'pk': new_finding_pk}))


################
# View Classes #
################


class FindingDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified finding. This view defaults
    to the finding_detail.html template.
    """
    model = Finding


class FindingCreate(LoginRequiredMixin, CreateView):
    """View for creating new findings. This view defaults to the
    finding_form.html template.
    """
    model = Finding
    form_class = FindingCreateForm

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(self.request, '%s was successfully created.' %
                         self.object.title, extra_tags='alert-success')
        return reverse('reporting:finding_detail', kwargs={'pk': self.object.pk})


class FindingUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing findings. This view defaults to the
    finding_form.html template.
    """
    model = Finding
    fields = '__all__'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(self.request, 'Master record for %s was '
                         'successfully updated.' % self.get_object().title,
                         extra_tags='alert-success')
        return reverse('reporting:finding_detail', kwargs={'pk': self.object.pk})


class FindingDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing findings. This view defaults to the
    finding_confirm_delete.html template.
    """
    model = Finding
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return a message after deletion."""
        messages.warning(self.request, 'Master record for %s was successfully '
                         'deleted.' % self.get_object().title,
                         extra_tags='alert-warning')
        return reverse_lazy('reporting:findings')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(FindingDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'finding master record'
        ctx['object_to_be_deleted'] = queryset.title
        return ctx


class ReportDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified report. This view defaults to the
    report_detail.html template.
    """
    model = Report


class ReportCreate(LoginRequiredMixin, CreateView):
    """View for creating new reports. This view defaults to the
    report_form.html template.
    """
    model = Report
    form_class = ReportCreateForm

    def form_valid(self, form):
        """Override form_valid to perform additional actions on new entries."""
        from ghostwriter.rolodex.models import Project
        project = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        form.instance.project = project
        form.instance.created_by = self.request.user
        self.request.session['active_report'] = {}
        self.request.session['active_report']['title'] = form.instance.title
        return super().form_valid(form)

    def get_initial(self):
        """Set the initial values for the form."""
        from ghostwriter.rolodex.models import Project
        project = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        title = '{} {} ({}) Report'.format(
            project.client,
            project.project_type,
            project.start_date)
        return {
                'title': title,
               }

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        self.request.session['active_report']['id'] = self.object.pk
        self.request.session.modified = True
        messages.success(self.request, 'New report was successfully created '
                         'and is now your active report.',
                         extra_tags='alert-success')
        return reverse('reporting:report_detail', kwargs={'pk': self.object.pk})


class ReportUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing reports. This view defaults to the
    report_form.html template.
    """
    model = Report
    fields = ('title', 'complete')

    def form_valid(self, form):
        """Override form_valid to perform additional actions on update."""
        self.request.session['active_report'] = {}
        self.request.session['active_report']['id'] = form.instance.id
        self.request.session['active_report']['title'] = form.instance.title
        self.request.session.modified = True
        return super().form_valid(form)

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(self.request, 'Report was updated successfully.',
                         extra_tags='alert-success')
        return reverse('reporting:report_detail', kwargs={'pk': self.object.pk})


class ReportDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing reports. This view defaults to the
    report_confirm_delete.html
    template.
    """
    model = Report
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        self.request.session['active_report'] = {}
        self.request.session['active_report']['id'] = ''
        self.request.session['active_report']['title'] = ''
        self.request.session.modified = True
        messages.warning(self.request, 'Report and associated evidence files '
                         'were deleted successfully.',
                         extra_tags='alert-warning')
        return reverse_lazy('reporting:reports')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ReportDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'entire report, evidence and all'
        ctx['object_to_be_deleted'] = queryset.title
        return ctx


class ReportFindingLinkUpdate(LoginRequiredMixin, UpdateView):
    """View for updating the local copies of a finding linked to a report.
    This view defaults to the local_edit.html template."""
    model = ReportFindingLink
    form_class = ReportFindingLinkUpdateForm
    template_name = 'reporting/local_edit.html'
    success_url = reverse_lazy('reporting:reports')

    def get_form(self, form_class=None):
        """Override the function to set a custom queryset for the form."""
        from ghostwriter.rolodex.models import ProjectAssignment
        form = super(ReportFindingLinkUpdate, self).get_form(form_class)
        user_primary_keys = ProjectAssignment.objects.\
            filter(project=self.object.report.project).\
            values_list('operator', flat=True)
        form.fields['assigned_to'].queryset = User.objects.\
            filter(id__in=user_primary_keys)
        return form

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(self.request, '%s was successfully updated.' %
                         self.get_object().title, extra_tags='alert-success')
        return reverse('reporting:report_detail', kwargs={'pk': self.object.report.id})


class ReportFindingLinkDelete(LoginRequiredMixin, DeleteView):
    """View for updating the local copies of a finding linked to a report.
    This view defaults to the local_remove.html template."""
    model = ReportFindingLink
    template_name = 'reporting/local_remove.html'

    def get_success_url(self, **kwargs):
        """Override function to return to the report."""
        messages.warning(self.request, '%s was removed from this report.' %
                         self.get_object().title, extra_tags='alert-warning')
        return reverse_lazy('reporting:report_detail', args=(self.report_pk,))

    def delete(self, request, *args, **kwargs):
        """Override function to save the report ID before deleting the
        finding.
        """
        self.report_pk = self.get_object().report.pk
        return super(ReportFindingLinkDelete, self).\
            delete(request, *args, **kwargs)


class EvidenceDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified evidence file. This view
    defaults to the evidence_detail.html template.
    """
    model = Evidence


class EvidenceUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing evidence. This view defaults to the
    evidence_form.html template.
    """
    model = Evidence
    form_class = EvidenceForm

    def get_success_url(self):
        """Override the function to return to the report after updates."""
        messages.success(self.request, '%s was successfully updated.' %
                         self.get_object().friendly_name,
                         extra_tags='alert-success')
        return reverse(
            'reporting:report_detail',
            kwargs={'pk': self.object.finding.report.pk})


class EvidenceDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing evidence. This view defaults to the
    evidence_confirm_delete.html template.
    """
    model = Evidence
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the report after deletion."""
        messages.warning(self.request, '%s was removed from this report and '
                         'the associated file has been deleted.' %
                         self.get_object().friendly_name,
                         extra_tags='alert-warning')
        return reverse(
            'reporting:report_detail',
            kwargs={'pk': self.object.finding.report.pk})

    def delete(self, request, *args, **kwargs):
        """Override function to save the report ID before deleting the
        finding.
        """
        full_path = os.path.join(
            settings.MEDIA_ROOT,
            self.get_object().document.name)
        directory = os.path.dirname(full_path)
        os.remove(full_path)
        # Try to delete the directory tree if this was the last/only file
        try:
            os.removedirs(directory)
        except Exception:
            pass
        return super(EvidenceDelete, self).delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(EvidenceDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'evidence file'
        ctx['object_to_be_deleted'] = queryset.friendly_name
        return ctx


class FindingNoteCreate(LoginRequiredMixin, CreateView):
    """View for creating new note entries. This view defaults to the
    note_form.html template.
    """
    model = FindingNote
    form_class = FindingNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully added to this finding.',
            extra_tags='alert-success')
        return reverse('reporting:finding_detail', kwargs={'pk': self.object.finding.id})

    def get_initial(self):
        """Set the initial values for the form."""
        finding_instance = get_object_or_404(
            Finding, pk=self.kwargs.get('pk'))
        finding = finding_instance
        return {
                'finding': finding,
                'operator': self.request.user
               }


class FindingNoteUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing note entries. This view defaults to the
    note_form.html template.
    """
    model = FindingNote
    form_class = FindingNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully updated.',
            extra_tags='alert-success')
        return reverse('reporting:finding_detail', kwargs={'pk': self.object.finding.pk})


class FindingNoteDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing note entries. This view defaults to the
    confirm_delete.html template.
    """
    model = FindingNote
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the server after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('reporting:finding_detail', kwargs={'pk': self.object.finding.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(FindingNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'note'
        ctx['object_to_be_deleted'] = queryset.note
        return ctx


class LocalFindingNoteCreate(LoginRequiredMixin, CreateView):
    """View for creating new note entries. This view defaults to the
    note_form.html template.
    """
    model = LocalFindingNote
    form_class = LocalFindingNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully added to this finding.',
            extra_tags='alert-success')
        return reverse('reporting:local_edit', kwargs={'pk': self.object.finding.id})

    def get_initial(self):
        """Set the initial values for the form."""
        finding_instance = get_object_or_404(
            ReportFindingLink, pk=self.kwargs.get('pk'))
        finding = finding_instance
        return {
                'finding': finding,
                'operator': self.request.user
               }


class LocalFindingNoteUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing note entries. This view defaults to the
    note_form.html template.
    """
    model = LocalFindingNote
    form_class = LocalFindingNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully updated.',
            extra_tags='alert-success')
        return reverse('reporting:local_edit', kwargs={'pk': self.object.finding.pk})


class LocalFindingNoteDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing note entries. This view defaults to the
    confirm_delete.html template.
    """
    model = LocalFindingNote
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the server after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('reporting:local_edit', kwargs={'pk': self.object.finding.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(LocalFindingNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'note'
        ctx['object_to_be_deleted'] = queryset.note
        return ctx
