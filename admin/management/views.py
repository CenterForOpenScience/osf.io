from dateutil.parser import isoparse
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.mixins import PermissionRequiredMixin

from osf.management.commands.manage_switch_flags import manage_waffle
from osf.management.commands.update_registration_schemas import update_registration_schemas
from osf.management.commands.daily_reporters_go import daily_reporters_go
from osf.management.commands.monthly_reporters_go import monthly_reporters_go
from osf.management.commands.fetch_cedar_metadata_templates import ingest_cedar_metadata_templates
from osf.management.commands.sync_doi_metadata import sync_doi_metadata, sync_doi_empty_metadata_dataarchive_registrations
from scripts.find_spammy_content import manage_spammy_content
from django.urls import reverse
from django.shortcuts import redirect
from osf.metrics.utils import YearMonth
from osf.models import Preprint, Node, Registration


class ManagementCommands(TemplateView):
    '''Basic form to trigger various management commands'''

    template_name = 'management/commands.html'
    object_type = 'management'

class ManagementCommandPermissionView(View, PermissionRequiredMixin):

    permission_required = 'osf.view_management'

class WaffleFlag(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        manage_waffle()
        messages.success(request, 'Waffle flags have been successfully updated.')
        return redirect(reverse('management:commands'))


class UpdateRegistrationSchemas(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        update_registration_schemas()
        messages.success(request, 'Registration schemas have been successfully updated.')
        return redirect(reverse('management:commands'))

class GetSpamDataCSV(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        days = int(request.POST.get('days_get', 0))
        models = []
        fast = False
        if request.POST.get('preprint_get', None):
            models.append(Preprint)
        if request.POST.get('node_get', None):
            models.append(Node)
        if request.POST.get('registration_get', None):
            models.append(Registration)
        if request.POST.get('fast_get', None):
            fast = True
        regex = request.POST.get('regex_get', None)
        if not days:
            messages.error(request, 'A number of days over 0 must be specified. Check your inputs and try again')
            return redirect(reverse('management:commands'))
        if not models:
            messages.error(request, 'At least one model must be specified. Check your inputs and try again')
            return redirect(reverse('management:commands'))
        if not regex:
            messages.error(request, 'A regular expression input must be specified. Check your inputs and try again')
            return redirect(reverse('management:commands'))
        response = HttpResponse(content_type='text/csv')
        manage_spammy_content(regex, days, models, response_object=response, fast=fast)
        filename = 'spam_document.csv'
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

class BanSpamByRegex(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        days = int(request.POST.get('days_ban', 0))
        models = []
        if request.POST.get('preprint_ban', None):
            models.append(Preprint)
        if request.POST.get('node_ban', None):
            models.append(Node)
        if request.POST.get('registration_ban', None):
            models.append(Registration)
        regex = request.POST.get('regex_ban', None)
        if not days:
            messages.error(request, 'A number of days over 0 must be specified. Check your inputs and try again')
            return redirect(reverse('management:commands'))
        if not models:
            messages.error(request, 'At least one model must be specified. Check your inputs and try again')
            return redirect(reverse('management:commands'))
        if not regex:
            messages.error(request, 'A regular expression input must be specified. Check your inputs and try again')
            return redirect(reverse('management:commands'))
        spam_ban_count = manage_spammy_content(regex, days, models, ban=True)
        messages.success(request, f'{spam_ban_count} users have been banned')
        return redirect(reverse('management:commands'))


class DailyReportersGo(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        report_date = request.POST.get('report_date', None)
        if report_date:
            report_date = isoparse(report_date).date()
        else:
            report_date = None

        daily_reporters_go.apply_async(kwargs={
            'report_date': report_date,
        })
        messages.success(request, 'Daily reporters going!')
        return redirect(reverse('management:commands'))


class MonthlyReportersGo(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        monthly_report_date = request.POST.get('monthly_report_date', None)
        if monthly_report_date:
            report_date = isoparse(monthly_report_date).date()
        else:
            report_date = None

        errors = monthly_reporters_go(
            yearmonth=(
                str(YearMonth.from_date(report_date))
                if report_date is not None
                else ''
            ),
        )

        if errors:
            for reporter_name, error_msg in errors.items():
                messages.error(request, f'{reporter_name} failed: {error_msg}')
        else:
            messages.success(request, 'Monthly reporters successfully went.')
        return redirect(reverse('management:commands'))


class IngestCedarMetadataTemplates(ManagementCommandPermissionView):
    def post(self, request):
        ingest_cedar_metadata_templates()
        messages.success(request, 'Cedar templates have been successfully imported from Cedar Workbench.')
        return redirect(reverse('management:commands'))


class BulkResync(ManagementCommandPermissionView):

    def post(self, request):
        sync_doi_metadata.apply_async(kwargs={
            'modified_date': timezone.now(),
            'batch_size': None,
            'dry_run': False
        })
        messages.success(request, 'Resyncing with CrossRef and DataCite! It will take some time.')
        return redirect(reverse('management:commands'))


class EmptyMetadataDataarchiveRegistrationBulkResync(ManagementCommandPermissionView):

    def post(self, request):
        sync_doi_empty_metadata_dataarchive_registrations.apply_async(kwargs={
            'modified_date': timezone.now(),
            'batch_size': None,
            'dry_run': False
        })
        messages.success(request, 'Resyncing with DataCite! It will take some time.')
        return redirect(reverse('management:commands'))
