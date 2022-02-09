from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.mixins import PermissionRequiredMixin

from osf.management.commands.manage_switch_flags import manage_waffle
from osf.management.commands.update_registration_schemas import update_registration_schemas
from osf.management.commands.transfer_quickfiles_to_projects import reverse_remove_quickfiles, remove_quickfiles
from osf.management.commands.reindex_quickfiles import reindex_quickfiles
from scripts.find_spammy_content import manage_spammy_content
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
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
        if request.POST.get('preprint_get', None):
            models.append(Preprint)
        if request.POST.get('node_get', None):
            models.append(Node)
        if request.POST.get('registration_get', None):
            models.append(Registration)
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
        manage_spammy_content(regex, days, models, response_object=response)
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


class MigrateQuickfiles(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'run':
            remove_quickfiles(dry_run=False)
            messages.success(request, 'quickfiles removed')

        if action == 'reverse':
            reverse_remove_quickfiles(dry_run=False)
            messages.success(request, 'quickfiles restored')

        return redirect(reverse('management:commands'))


class ReindexQuickfiles(ManagementCommandPermissionView):

    def post(self, request, *args, **kwargs):
        reindex_quickfiles(dry_run=False)
        messages.success(request, 'quickfiles reindexed')

        return redirect(reverse('management:commands'))
