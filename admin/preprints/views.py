from __future__ import unicode_literals

from django.views.generic import ListView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from osf.models import SpamStatus
from osf.models.preprint_service import PreprintService
from osf.models.admin_log_entry import update_admin_log, REINDEX_SHARE, CONFIRM_SPAM, CONFIRM_HAM
from website.preprints.tasks import update_preprint_share
from website.project.views.register import osf_admin_change_status_identifier

from framework.exceptions import PermissionsError
from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.preprints.serializers import serialize_preprint
from admin.preprints.forms import ChangeProviderForm


class PreprintFormView(PermissionRequiredMixin, GuidFormView):
    """ Allow authorized admin user to input specific preprint guid.

    Basic form. No admin models.
    """
    template_name = 'preprints/search.html'
    object_type = 'preprint'
    permission_required = 'osf.view_preprintservice'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(PermissionRequiredMixin, UpdateView, GuidView):
    """ Allow authorized admin user to view preprints

    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprintservice'
    permission_required = 'osf.view_preprintservice'
    raise_exception = True
    form_class = ChangeProviderForm

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs.get('guid')})

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.change_preprintservice'):
            raise PermissionsError("This user does not have permission to update this preprint's provider.")
        return super(PreprintView, self).post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return PreprintService.load(self.kwargs.get('guid'))

    def get_context_data(self, **kwargs):
        preprint = PreprintService.load(self.kwargs.get('guid'))
        # TODO - we shouldn't need this serialized_preprint value -- https://openscience.atlassian.net/browse/OSF-7743
        kwargs['serialized_preprint'] = serialize_preprint(preprint)
        kwargs['change_provider_form'] = ChangeProviderForm(instance=preprint)
        kwargs.update({'SPAM_STATUS': SpamStatus})  # Pass spam status in to check against

        return super(PreprintView, self).get_context_data(**kwargs)

class PreprintSpamList(PermissionRequiredMixin, ListView):
    SPAM_STATE = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = ('created')
    context_object_name = 'preprintservice'
    permission_required = ('osf.view_spam', 'osf.view_preprintservice')
    raise_exception = True

    def get_queryset(self):
        return PreprintService.objects.filter(spam_status=self.SPAM_STATE).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'preprints': map(serialize_preprint, query_set),
            'page': page,
        }

class PreprintFlaggedSpamList(PreprintSpamList, DeleteView):
    SPAM_STATE = SpamStatus.FLAGGED
    template_name = 'preprints/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm('auth.mark_spam'):
            raise PermissionDenied('You do not have permission to update a preprint flagged as spam.')
        preprint_ids = [
            pid for pid in request.POST.keys()
            if pid != 'csrfmiddlewaretoken'
        ]
        for pid in preprint_ids:
            preprint = PreprintService.load(pid)
            osf_admin_change_status_identifier(preprint, 'unavailable | spam')
            preprint.confirm_spam(save=True)
            update_admin_log(
                user_id=self.request.user.id,
                object_id=pid,
                object_repr='PreprintService',
                message='Confirmed SPAM: {}'.format(pid),
                action_flag=CONFIRM_SPAM
            )
        return redirect('preprints:flagged-spam')

class PreprintKnownSpamList(PreprintSpamList):
    SPAM_STATE = SpamStatus.SPAM
    template_name = 'preprints/known_spam_list.html'

class PreprintKnownHamList(PreprintSpamList):
    SPAM_STATE = SpamStatus.HAM
    template_name = 'preprints/known_spam_list.html'

class PreprintDeleteBase(DeleteView):
    template_name = None
    context_object_name = 'preprintservice'
    object = None

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(PreprintDeleteBase, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return PreprintService.load(self.kwargs.get('guid'))


class PreprintConfirmSpamView(PermissionRequiredMixin, PreprintDeleteBase):
    template_name = 'preprints/confirm_spam.html'
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.confirm_spam(save=True)
        osf_admin_change_status_identifier(preprint, 'unavailable | spam')
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='PreprintService',
            message='Confirmed SPAM: {}'.format(preprint._id),
            action_flag=CONFIRM_SPAM,
        )
        return redirect(reverse_preprint(self.kwargs.get('guid')))

class PreprintConfirmHamView(PermissionRequiredMixin, PreprintDeleteBase):
    template_name = 'preprints/confirm_ham.html'
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.confirm_ham(save=True)
        osf_admin_change_status_identifier(preprint, 'public')
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='PreprintService',
            message='Confirmed HAM: {}'.format(preprint._id),
            action_flag=CONFIRM_HAM
        )
        return redirect(reverse_preprint(self.kwargs.get('guid')))

class PreprintReindexShare(PermissionRequiredMixin, PreprintDeleteBase):
    template_name = 'preprints/reindex_preprint_share.html'
    permission_required = 'osf.view_preprintservice'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        update_preprint_share(preprint)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Preprint',
            message='Preprint Reindexed (SHARE): {}'.format(preprint._id),
            action_flag=REINDEX_SHARE
        )
        return redirect(reverse_preprint(self.kwargs.get('guid')))
