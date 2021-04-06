from django.views.generic import TemplateView, View
from django.contrib import messages
from osf.management.commands.manage_switch_flags import manage_waffle
from osf.management.commands.update_registration_schemas import update_registration_schemas
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

class ManagementCommands(TemplateView):
    """ Basic form to trigger various management commands
    """
    template_name = 'management/commands.html'
    object_type = 'management'

class WaffleFlag(View):

    def post(self, request, *args, **kwargs):
        manage_waffle()
        messages.success(request, 'Waffle flags have been successfully updated.')
        return redirect(reverse('management:commands'))


class UpdateRegistrationSchemas(View):

    def post(self, request, *args, **kwargs):
        update_registration_schemas()
        messages.success(request, 'Registration schemas have been successfully updated.')
        return redirect(reverse('management:commands'))
