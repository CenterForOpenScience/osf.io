from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView, View

from admin.base.forms import GuidForm
from admin.guids.forms import ReassignGuidForm
from osf.models import AbstractNode, Collection, Guid, OSFUser
from osf.models.admin_log_entry import REMOVE_GUID, update_admin_log
from osf.models.base import GuidReassignError, reassign_guid


def get_referent_admin_url(referent):
    """Admin page of the object a guid points to, or None if it has no admin page."""
    if isinstance(referent, OSFUser):
        return reverse('users:user', kwargs={'guid': referent._id})
    if isinstance(referent, AbstractNode):
        return reverse('nodes:node', kwargs={'guid': referent._id})
    return None


def describe_referent(referent):
    if isinstance(referent, Collection) and referent.is_bookmark_collection:
        return f'Bookmark collection (owner: {referent.creator._id})'
    return f'{type(referent).__name__} {referent.pk}'


class GuidSearchView(PermissionRequiredMixin, FormView):
    """Look up a guid to see what it points to."""
    template_name = 'guids/search.html'
    permission_required = 'osf.view_guid'
    raise_exception = True
    form_class = GuidForm

    def form_valid(self, form):
        return redirect(reverse('guids:detail', kwargs={'guid': form.cleaned_data['guid'].strip().lower()}))


class GuidDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'guids/detail.html'
    permission_required = 'osf.view_guid'
    raise_exception = True

    def get_context_data(self, **kwargs):
        guid = Guid.load(self.kwargs['guid'])
        if guid is None:
            raise Http404(f'Guid not found: {self.kwargs["guid"]}')
        referent = guid.referent
        kwargs.update({
            'guid': guid,
            'referent': referent,
            'referent_description': describe_referent(referent) if referent is not None else None,
            'referent_url': get_referent_admin_url(referent) if referent is not None else None,
            'form': ReassignGuidForm(),
        })
        return super().get_context_data(**kwargs)


class GuidReassignView(PermissionRequiredMixin, View):
    """Remove a guid from its object and give the object a new one, freeing the old id."""
    permission_required = 'osf.remove_guid'
    raise_exception = True
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        guid_str = self.kwargs['guid']
        detail_url = reverse('guids:detail', kwargs={'guid': guid_str})
        form = ReassignGuidForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A justification is required.')
            return redirect(detail_url)
        try:
            with transaction.atomic():
                old_id, new_id, referent = reassign_guid(guid_str)
                update_admin_log(
                    user_id=request.user.id,
                    object_id=old_id,
                    object_repr=type(referent).__name__,
                    message=f'{form.cleaned_data["justification"]} (old={old_id}, new={new_id}, referent={describe_referent(referent)})',
                    action_flag=REMOVE_GUID,
                )
        except GuidReassignError as exc:
            messages.error(request, str(exc))
            return redirect(detail_url)
        messages.success(request, f'Guid {old_id} was removed. The object now has guid {new_id}.')
        return redirect(reverse('guids:detail', kwargs={'guid': new_id}))
