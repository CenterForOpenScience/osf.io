import datetime
from io import StringIO

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
            report_date = datetime.date.fromisoformat(report_date)
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
        start_date = request.POST.get('monthly_report_start_date', None)
        end_date = request.POST.get('monthly_report_end_date', None)
        reporter_key = request.POST.get('reporter_key', '')
        _start_ym = (
            YearMonth.from_date(datetime.date.fromisoformat(start_date))
            if start_date
            else YearMonth.from_today().prior()
        )
        _inclusive_end_ym = (
            YearMonth.from_date(datetime.date.fromisoformat(end_date))
            if end_date
            else _start_ym
        )
        _reporter_display = reporter_key or 'all monthly reporters'
        _each_ym = list(YearMonth.range(_start_ym, _inclusive_end_ym.next()))
        if _each_ym:
            for _ym in _each_ym:
                call_command('monthly_reporters_go', yearmonth=str(_ym), reporter=reporter_key)
                messages.success(request, f'Scheduled {_reporter_display} for {_ym}')
        else:
            messages.error(f'nothing doing between {_start_ym} and {_inclusive_end_ym}')
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
        run_type = request.POST.get('run_type')
        if run_type == 'restore_one':
            template_name = request.POST.get('template_name')
            if not template_name:
                messages.error(request, 'A template name must be specified when restoring one template. Check your inputs and try again')
                return redirect(reverse('management:commands'))
            populate_notification_types(restore_one=template_name)
        elif run_type == 'restore_all':
            populate_notification_types(restore_all=True)
        else:
            populate_notification_types()
        messages.success(request, 'Notification templates have been successfully synced.')
        return redirect(reverse('management:commands'))


class RemoveOrcidFromUserSocial(ManagementCommandPermissionView):

    def post(self, request):
        remove_orcid_from_user_social()
        messages.success(request, 'Orcid from user social have been successfully removed.')
        return redirect(reverse('management:commands'))


class MigrateFunderNamesToRor(ManagementCommandPermissionView):

    def post(self, request):
        _command_kwargs = {}
        _out_io = StringIO()
        call_command('migrate_funder_names_to_ror', **_command_kwargs, stdout=_out_io)
        messages.success(request, 'ROR funder names have been successfully updated and made consistent.')
        for _line in _out_io.getvalue().split('\n'):
            messages.info(request, _line)
        return redirect(reverse('management:commands'))


class FixRestoredTrashedFiles(ManagementCommandPermissionView):

    def post(self, request):
        call_command('fix_restored_trashed_files')
        messages.success(request, 'Restored trashed files have been successfully fixed.')
        return redirect(reverse('management:commands'))
