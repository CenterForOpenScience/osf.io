from io import StringIO

from dateutil.parser import isoparse
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.management import call_command

from osf.management.commands.manage_switch_flags import manage_waffle
from osf.management.commands.update_registration_schemas import update_registration_schemas
from osf.management.commands.fetch_cedar_metadata_templates import ingest_cedar_metadata_templates
from osf.management.commands.sync_doi_metadata import sync_doi_metadata, sync_doi_empty_metadata_dataarchive_registrations
from osf.management.commands.populate_notification_types import populate_notification_types
from osf.management.commands.remove_orcid_from_user_social import remove_orcid_from_user_social
from scripts.find_spammy_content import manage_spammy_content
from django.urls import reverse
from django.shortcuts import redirect
from osf.metrics.utils import YearMonth
from osf.metrics.reporters import AllMonthlyReporters, AllDailyReporters
from osf.models import Preprint, Node, Registration


class ManagementCommands(TemplateView):
    '''Basic form to trigger various management commands'''

    template_name = 'management/commands.html'
    object_type = 'management'

    def get_context_data(self, **kwargs):
        _context = super().get_context_data(**kwargs)
        _context['monthly_reporter_keys'] = [
            _enum.name.lower() for _enum in AllMonthlyReporters
        ]
        _context['daily_reporter_keys'] = [
            _enum.name.lower() for _enum in AllDailyReporters
        ]
        return _context


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

        call_command(
            'daily_reporters_go',
            date=report_date,
            reporter=request.POST.get('reporter_key', ''),
        )
        messages.success(request, 'Daily reporters going!')
        return redirect(reverse('management:commands'))


class MonthlyReportersGo(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        monthly_report_date = request.POST.get('monthly_report_date', None)
        if monthly_report_date:
            report_date = isoparse(monthly_report_date).date()
        else:
            report_date = None

        reporter_key = request.POST.get('reporter_key', '')
        call_command(
            'monthly_reporters_go',
            yearmonth=(
                str(YearMonth.from_date(report_date))
                if report_date is not None
                else ''
            ),
            reporter=reporter_key,
        )
        if reporter_key:
            messages.success(request, f'Monthly reporter {reporter_key!r} going!')
        else:
            messages.success(request, 'Monthly reporters going!')
        return redirect(reverse('management:commands'))


class IngestCedarMetadataTemplates(ManagementCommandPermissionView):
    def post(self, request):
        ingest_cedar_metadata_templates()
        messages.success(request, 'Cedar templates have been successfully imported from Cedar Workbench.')
        return redirect(reverse('management:commands'))


class BulkResync(ManagementCommandPermissionView):

    def post(self, request):
        missing_dois_only = request.POST.get('missing_preprint_dois_only', False)
        sync_doi_metadata.apply_async(kwargs={
            'modified_date': timezone.now(),
            'batch_size': None,
            'dry_run': False,
            'missing_preprint_dois_only': missing_dois_only
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


class SyncNotificationTemplates(ManagementCommandPermissionView):

    def post(self, request):
        populate_notification_types()
        messages.success(request, 'Notification templates have been successfully synced.')
        return redirect(reverse('management:commands'))


class RemoveOrcidFromUserSocial(ManagementCommandPermissionView):

    def post(self, request):
        remove_orcid_from_user_social()
        messages.success(request, 'Orcid from user social have been successfully removed.')
        return redirect(reverse('management:commands'))


class MigrateOsfmetrics6to8(ManagementCommandPermissionView):
    def post(self, request):
        _command_kwargs = {
            'no_setup': True,
            'no_color': True,
            'no_counts': request.POST.get('no_counts'),
            'clear_state': request.POST.get('clear_state'),
            'clear_es8_data': request.POST.get('clear_es8_data'),
            'start': request.POST.get('start'),
            'unchanged': request.POST.get('unchanged'),
            'usage_reports': request.POST.get('usage_reports'),
            'usage_events': request.POST.get('usage_events'),
        }
        _out_io = StringIO()
        call_command('migrate_osfmetrics_6to8', **_command_kwargs, stdout=_out_io)
        for _line in _out_io.getvalue().split('\n'):
            messages.info(request, _line)
        return redirect(reverse('management:commands'))
