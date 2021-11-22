from __future__ import unicode_literals

from django.db.models import F
from django.views.generic import DeleteView, ListView, View
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from osf.models import (
    SpamStatus,
    PreprintRequest,
    PreprintProvider
)

from osf.models.preprint import Preprint, PreprintLog
from osf.models.admin_log_entry import (
    update_admin_log,
    REINDEX_ELASTIC,
    REINDEX_SHARE,
    PREPRINT_REMOVED,
    PREPRINT_RESTORED,
    CONFIRM_SPAM,
    CONFIRM_HAM,
    APPROVE_WITHDRAWAL,
    REJECT_WITHDRAWAL
)

from website import search, settings

from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.nodes.views import NodeRemoveContributorView
from admin.preprints.forms import ChangeProviderForm

from api.share.utils import update_share
from rest_framework.exceptions import PermissionDenied


class PreprintMixin(PermissionRequiredMixin):

    def get_object(self):
        preprint = Preprint.objects.get(guids___id=self.kwargs['guid'])
        preprint.guid = preprint._id
        return preprint

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs['guid']})


class PreprintFormView(GuidFormView):
    """ Allow authorized admin user to input specific preprint guid. """
    template_name = 'preprints/search.html'
    object_type = 'preprint'
    permission_required = 'osf.view_preprint'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(PreprintMixin, GuidView):
    """ Allow authorized admin user to view preprints """
    template_name = 'preprints/preprint.html'
    permission_required = ('osf.view_preprint', 'osf.change_preprint',)
    form_class = ChangeProviderForm

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()

        old_provider = preprint.provider
        new_provider = PreprintProvider.objects.get(id=request.POST['provider'])
        if old_provider != new_provider:
            subject_problems = preprint.map_subjects_between_providers(old_provider, new_provider, auth=None)
            if subject_problems:
                messages.warning(request, 'Unable to find subjects in new provider for the following subject(s):')
                for problem in subject_problems:
                    messages.warning(request, problem)
            preprint.provider = new_provider
            preprint.save()

        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        preprint = self.get_object()
        return super().get_context_data(**{
            'preprint': preprint,
            'SPAM_STATUS': SpamStatus,
            'message':  kwargs.get('message'),
            'form':   ChangeProviderForm(instance=preprint),
        })


class PreprintSpamList(PermissionRequiredMixin, ListView):
    SPAM_STATE = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = 'created'
    permission_required = ('osf.view_spam', 'osf.view_preprint')
    raise_exception = True

    def get_queryset(self):
        return Preprint.objects.filter(
            spam_status=self.SPAM_STATE
        ).order_by(
            self.ordering
        ).annotate(guid=F('guids___id'))  # Django template does not like attributes with underscores for some reason

    def get_context_data(self, **kwargs):
        page_size = self.get_paginate_by(self.object_list)
        paginator, page, query_set, is_paginated = self.paginate_queryset(self.object_list, page_size)
        return {
            'preprints': self.object_list,
            'page': page,
        }


class PreprintReindexShare(PreprintMixin, View):
    permission_required = 'osf.view_preprint'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        if settings.SHARE_ENABLED:
            update_share(preprint)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Preprint',
            message=f'Preprint Reindexed (SHARE): {preprint._id}',
            action_flag=REINDEX_SHARE
        )
        return redirect(self.get_success_url())


class PreprintReindexElastic(PreprintMixin, View):
    permission_required = 'osf.view_preprint'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        search.search.update_preprint(preprint, bulk=False, async_update=False)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Preprint',
            message=f'Preprint Reindexed (Elastic): {preprint._id}',
            action_flag=REINDEX_ELASTIC
        )
        return redirect(self.get_success_url())


class PreprintRemoveContributorView(PreprintMixin, NodeRemoveContributorView):
    """ Allow authorized admin user to remove preprint contributor. """
    permission_required = ('osf.view_preprint', 'osf.change_preprint')

    def add_contributor_removed_log(self, preprint, user):
        PreprintLog(
            action=PreprintLog.CONTRIB_REMOVED,
            user=None,
            params={
                'preprint': preprint._id,
                'contributors': user._id
            },
            should_hide=True,
        ).save()


class PreprintDeleteView(PreprintMixin, DeleteView):
    """ Reversible delete that allows authorized admin user to remove/hide preprints. """
    template_name = 'preprints/remove_preprint.html'
    permission_required = ('osf.view_preprint', 'osf.delete_preprint')

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        if preprint.deleted:
            preprint.deleted = None

            # Log invisibly on the OSF.
            update_admin_log(
                user_id=self.request.user.id,
                object_id=preprint.pk,
                object_repr='Preprint',
                message=f'Preprint {preprint.pk} restored.',
                action_flag=PREPRINT_RESTORED
            )
        else:
            preprint.deleted = timezone.now()
            PreprintLog(
                action=PreprintLog.DELETED,
                user=None,
                params={
                    'preprint': preprint._id,
                },
                should_hide=True,
            ).save()

            # Log invisibly on the OSF.
            update_admin_log(
                user_id=self.request.user.id,
                object_id=preprint.pk,
                object_repr='Preprint',
                message=f'Preprint {preprint._id} removed.',
                action_flag=PREPRINT_REMOVED
            )
        preprint.save()

        return redirect(self.get_success_url())


class PreprintWithdrawalRequestList(PermissionRequiredMixin, ListView):
    paginate_by = 10
    paginate_orphans = 1
    template_name = 'preprints/withdrawal_requests.html'
    ordering = '-created'
    permission_required = 'osf.change_preprintrequest'
    raise_exception = True

    def get_queryset(self):
        return PreprintRequest.objects.filter(
            request_type='withdrawal',
            target__provider__reviews_workflow=None
        ).exclude(
            machine_state='initial'
        ).order_by(
            self.ordering
        ).annotate(target_guid=F('target__guids___id'))

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        return {
            'requests': query_set,
            'page': page,
        }

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.change_preprintrequest'):
            raise PermissionDenied('You do not have permission to approve or reject withdrawal requests.')
        is_approve_action = 'approveRequest' in request.POST.keys()
        request_ids = [
            id_ for id_ in request.POST.keys()
            if id_ not in ['csrfmiddlewaretoken', 'approveRequest', 'rejectRequest']
        ]
        for id_ in request_ids:
            print(id_)
            withdrawal_request = PreprintRequest.objects.get(id=id_)
            if is_approve_action:
                withdrawal_request.run_accept(self.request.user, withdrawal_request.comment)
            else:
                withdrawal_request.run_reject(self.request.user, withdrawal_request.comment)
            update_admin_log(
                user_id=self.request.user.id,
                object_id=id_,
                object_repr='PreprintRequest',
                message='{} withdrawal request: {} of preprint {}'.format('Approved' if is_approve_action else 'Rejected', id_, withdrawal_request.target._id),
                action_flag=APPROVE_WITHDRAWAL if is_approve_action else REJECT_WITHDRAWAL
            )
        return redirect('preprints:withdrawal-requests')


class WithdrawalRequestMixin(PermissionRequiredMixin):
    permission_required = 'osf.change_preprintrequest'

    def get_object(self):
        return PreprintRequest.objects.filter(
            request_type='withdrawal',
            target__guids___id=self.kwargs['guid'],
            target__provider__reviews_workflow=None
        ).first()

    def get_success_url(self):
        return reverse_lazy('preprints:withdrawal-requests')


class PreprintApproveWithdrawalRequest(WithdrawalRequestMixin, View):

    def post(self, request, *args, **kwargs):
        withdrawal_request = self.get_object()
        withdrawal_request.run_accept(self.request.user, withdrawal_request.comment)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=withdrawal_request._id,
            object_repr='PreprintRequest',
            message=f'Approved withdrawal request: {withdrawal_request._id}',
            action_flag=APPROVE_WITHDRAWAL,
        )
        return redirect(self.get_success_url())


class PreprintRejectWithdrawalRequest(WithdrawalRequestMixin, View):

    def post(self, request, *args, **kwargs):
        withdrawal_request = self.get_object()
        withdrawal_request.run_reject(self.request.user, withdrawal_request.comment)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=withdrawal_request._id,
            object_repr='PreprintRequest',
            message=f'Rejected withdrawal request: {withdrawal_request._id}',
            action_flag=REJECT_WITHDRAWAL,
        )
        return redirect(self.get_success_url())


class PreprintFlaggedSpamList(PreprintSpamList, DeleteView):
    SPAM_STATE = SpamStatus.FLAGGED
    template_name = 'preprints/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.mark_spam'):
            raise PermissionDenied('You do not have permission to update a preprint flagged as spam.')
        preprint_ids = []
        for key in list(request.POST.keys()):
            if key == 'spam_confirm':
                action = 'SPAM'
                action_flag = CONFIRM_HAM
            elif key == 'ham_confirm':
                action = 'HAM'
                action_flag = CONFIRM_SPAM
            elif key != 'csrfmiddlewaretoken':
                preprint_ids.append(key)

        for pid in preprint_ids:
            preprint = Preprint.load(pid)

            if preprint.get_identifier_value('doi'):
                preprint.request_identifier_update(category='doi')

            if action == 'SPAM':
                preprint.confirm_spam(save=True)
            elif action == 'HAM':
                preprint.confirm_ham(save=True)

            update_admin_log(
                user_id=self.request.user.id,
                object_id=pid,
                object_repr='Preprint',
                message=f'Confirmed {action}: {pid}',
                action_flag=action_flag
            )
        return redirect('preprints:flagged-spam')


class PreprintKnownSpamList(PreprintSpamList):
    SPAM_STATE = SpamStatus.SPAM
    template_name = 'preprints/known_spam_list.html'


class PreprintKnownHamList(PreprintSpamList):
    SPAM_STATE = SpamStatus.HAM
    template_name = 'preprints/known_spam_list.html'


class PreprintConfirmSpamView(PreprintMixin, View):
    permission_required = 'osf.mark_spam'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.confirm_spam(save=True)

        if preprint.get_identifier_value('doi'):
            preprint.request_identifier_update(category='doi')

        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='preprint',
            message=f'Confirmed SPAM: {preprint._id}',
            action_flag=CONFIRM_SPAM
        )

        return redirect(reverse_preprint(self.kwargs.get('guid')))


class PreprintConfirmHamView(PreprintMixin, View):
    permission_required = 'osf.mark_spam'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.confirm_ham(save=True)

        if preprint.get_identifier_value('doi'):
            preprint.request_identifier_update(category='doi')

        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='preprint',
            message=f'Confirmed HAM: {preprint._id}',
            action_flag=CONFIRM_HAM
        )

        return redirect(reverse_preprint(self.kwargs.get('guid')))
