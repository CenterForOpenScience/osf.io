from django.views.generic import TemplateView, View
from osf.management.commands.manage_switch_flags import manage_waffle
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
        return redirect(reverse('management:commands'))
