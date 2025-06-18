from django.urls import NoReverseMatch, reverse
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView
from django.views.generic import DetailView

from admin.base.forms import GuidForm
from admin.nodes.queries import STORAGE_USAGE_QUERY
from admin.nodes.views import StorageMixin

from osf.models.registrations import DraftRegistration


class DraftRegistrationMixin(PermissionRequiredMixin):

    def get_object(self):
        draft_registration = DraftRegistration.objects.filter(
            _id=self.kwargs['draft_registration_id']
        ).annotate(
            **STORAGE_USAGE_QUERY
        ).first()
        draft_registration.guid = draft_registration._id
        return draft_registration

    def get_success_url(self):
        return reverse('draft_registrations:detail', kwargs={
            'draft_registration_id': self.kwargs['draft_registration_id']
        })


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
                return redirect(reverse('users:draft-registrations', kwargs={'guid': guid}))
            except NoReverseMatch as e:
                messages.error(self.request, str(e))

        return super().form_valid(form)


class DraftRegistrationView(DraftRegistrationMixin, DetailView):
    """ Allows authorized users to view draft registration
    """
    template_name = 'draft_registrations/detail.html'
    permission_required = 'osf.view_draftregistration'

    def get_context_data(self, **kwargs):
        draft_registration = self.get_object()
        return super().get_context_data(**{
            'draft_registration': draft_registration
        }, **kwargs)


class DraftRegisrationModifyStorageUsage(DraftRegistrationMixin, StorageMixin):
    template_name = 'draft_registrations/detail.html'
    permission_required = 'osf.change_draftregistration'
