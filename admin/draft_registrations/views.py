from django.urls import NoReverseMatch, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView

from admin.base.forms import GuidForm


class UserDraftRegistrationSearchView(PermissionRequiredMixin, FormView):
    """ Allows authorized users to search for user's draft registrations by his guid.
    """
    template_name = 'draft_registrations/search.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = GuidForm

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        if guid:
            try:
                return redirect(reverse_lazy('users:draft-registrations', kwargs={'guid': guid}))
            except NoReverseMatch as e:
                messages.error(self.request, str(e))

        return super().form_valid(form)
