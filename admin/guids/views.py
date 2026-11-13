import logging

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.views.generic import FormView, TemplateView, View

from admin.base.forms import GuidForm
from admin.guids.forms import ReassignGuidForm
from osf.models import AbstractNode, BaseFileNode, Collection, Guid, OSFUser, Preprint
from osf.models.admin_log_entry import REMOVE_GUID, update_admin_log
from osf.models.base import GuidReassignError, guid_reassign_blocker, reassign_guid


logger = logging.getLogger(__name__)


def get_referent_admin_url(referent):
    """Admin page of the object a guid points to, or None if it has no admin page."""
    if isinstance(referent, OSFUser):
        return reverse('users:user', kwargs={'guid': referent._id})
    if isinstance(referent, AbstractNode):  # nodes and registrations share one admin page
        return reverse('nodes:node', kwargs={'guid': referent._id})
    if isinstance(referent, Preprint):
        return reverse('preprints:preprint', kwargs={'guid': referent._id})
    if isinstance(referent, BaseFileNode) and referent.target is not None:
        return get_referent_admin_url(referent.target)  # files have no admin page of their own
    return None


def describe_referent(referent):
    if isinstance(referent, Collection) and referent.is_bookmark_collection:
        return f'Bookmark collection (owner: {referent.creator._id})'
    if isinstance(referent, BaseFileNode):
        target = referent.target
        target_id = getattr(target, '_id', None)
        return f'File {referent.materialized_path or referent.name} ({referent.provider}) of {type(target).__name__} {target_id}'
    if isinstance(referent, Preprint):
        return f'Preprint {referent._id} "{referent.title}"'
    return f'{type(referent).__name__} {referent.pk}'


def version_guid_error(guid_str):
    base_guid_str, version = Guid.split_guid(guid_str)
    if version is None:
        return None
    return (
        f'"{guid_str}" is a preprint guid. Version guids cannot be reassigned'
    )


class GuidSearchView(PermissionRequiredMixin, FormView):
    """Look up a guid to see what it points to."""
    template_name = 'guids/search.html'
    permission_required = 'osf.view_guid'
    raise_exception = True
    form_class = GuidForm

    def form_valid(self, form):
        guid_str = form.cleaned_data['guid'].strip().lower()
        error = version_guid_error(guid_str)
        if error is None:
            try:
                return redirect(reverse('guids:detail', kwargs={'guid': guid_str}))
            except NoReverseMatch:
                error = f'"{guid_str}" is not a valid guid.'
        form.add_error('guid', error)
        return self.form_invalid(form)


class GuidDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'guids/detail.html'
    permission_required = 'osf.view_guid'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        error = version_guid_error(self.kwargs['guid'])
        if error:
            messages.error(request, error)
            return redirect(reverse('guids:search'))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        guid = Guid.load(self.kwargs['guid'])
        if guid is None:
            raise Http404(f'Guid not found: {self.kwargs["guid"]}')
        referent = guid.referent
        reassign_blocker = guid_reassign_blocker(referent) if referent is not None else None
        kwargs.update({
            'guid': guid,
            'guid_id': guid._id,
            'referent': referent,
            'referent_description': describe_referent(referent) if referent is not None else None,
            'referent_url': get_referent_admin_url(referent) if referent is not None else None,
            'reassign_blocker': reassign_blocker,
            'can_reassign': referent is not None and reassign_blocker is None,
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
                referent_description = describe_referent(referent)
                update_admin_log(
                    user_id=request.user.id,
                    object_id=old_id,
                    object_repr=type(referent).__name__,
                    message=f'{form.cleaned_data["justification"]} (old={old_id}, new={new_id}, referent={referent_description})',
                    action_flag=REMOVE_GUID,
                )
        except GuidReassignError as exc:
            messages.error(request, str(exc))
            return redirect(detail_url)
        # Logged after the transaction commits so cloud logs show what happened and the change can be reversed.
        logger.warning(
            'Admin guid reassignment: old_guid=%s new_guid=%s referent_type=%s referent_pk=%s referent=%s '
            'admin_user_pk=%s admin_user_guid=%s justification=%s',
            old_id, new_id, type(referent).__name__, referent.pk, referent_description,
            request.user.id, getattr(request.user, '_id', None), form.cleaned_data['justification'],
        )
        messages.success(request, f'Guid {old_id} was removed. The object now has guid {new_id}.')
        return redirect(reverse('guids:detail', kwargs={'guid': new_id}))
