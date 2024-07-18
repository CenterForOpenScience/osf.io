from django.db.models import F
from django.core.exceptions import PermissionDenied
from django.urls import NoReverseMatch
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import (
    View,
    ListView,
    FormView,
)
from django.utils import timezone
from django.urls import reverse_lazy

from admin.base.views import GuidView
from admin.base.forms import GuidForm
from admin.nodes.views import NodeRemoveContributorView
from admin.preprints.forms import ChangeProviderForm, MachineStateForm

from api.share.utils import update_share

from osf.exceptions import PreprintStateError

from osf.models import (
    SpamStatus,
    Preprint,
    PreprintLog,
    PreprintRequest,
    PreprintProvider
)

from osf.models.admin_log_entry import (
    update_admin_log,
    REINDEX_ELASTIC,
    REINDEX_SHARE,
    PREPRINT_REMOVED,
    PREPRINT_RESTORED,
    CONFIRM_SPAM,
    CONFIRM_HAM,
    APPROVE_WITHDRAWAL,
    REJECT_WITHDRAWAL,
    UNFLAG_SPAM,
)

from website import search


class PreprintMixin(PermissionRequiredMixin):

    def get_object(self):
        preprint = Preprint.objects.get(guids___id=self.kwargs['guid'])
        # Django template does not like attributes with underscores for some reason
        preprint.guid = preprint._id
        return preprint

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs['guid']})


class PreprintView(PreprintMixin, GuidView):
    """ Allows authorized users to view preprint info and change a preprint's provider.
    """
    template_name = 'preprints/preprint.html'
    permission_required = ('osf.view_preprint', 'osf.change_preprint',)

    def get_context_data(self, **kwargs):
        preprint = self.get_object()
        return super().get_context_data(**{
            'preprint': preprint,
            'SPAM_STATUS': SpamStatus,
            'change_provider_form': ChangeProviderForm(instance=preprint),
            'change_machine_state_form': MachineStateForm(instance=preprint),
        }, **kwargs)


class PreprintProviderChangeView(PreprintMixin, GuidView):
    """ Allows authorized users to view preprint info and change a preprint's provider.
    """
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


class PreprintMachineStateView(PreprintMixin, GuidView):
    """ Allows authorized users to view preprint info and change a preprint's machine_state.
    """
    permission_required = ('osf.view_preprint', 'osf.change_preprint',)
    form_class = MachineStateForm

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        new_machine_state = request.POST['machine_state']
        if preprint.machine_state != new_machine_state:
            preprint.machine_state = new_machine_state
            preprint.save()
            preprint.refresh_from_db()

        return redirect(self.get_success_url())


class PreprintSearchView(PermissionRequiredMixin, FormView):
    """ Allows authorized users to search for a specific preprint by guid.
    """
    template_name = 'preprints/search.html'
    permission_required = 'osf.view_preprint'
    raise_exception = True
    form_class = GuidForm

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        if guid:
            try:
                return redirect(reverse_lazy('preprints:preprint', kwargs={'guid': guid}))
            except NoReverseMatch as e:
                messages.error(self.request, str(e))

        return super().form_valid(form)


class PreprintSpamList(PermissionRequiredMixin, ListView):
    """ Allows authorized users to view a list of preprint that have a particular spam status.
    """
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
    """ Allows an authorized user to reindex a preprint in SHARE.
    """
    permission_required = 'osf.view_preprint'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
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
    """ Allows an authorized user to reindex a node in ElasticSearch.
    """
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
    """ Allows authorized users to remove contributors from preprints.
    """
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


class PreprintDeleteView(PreprintMixin, View):
    """ Allows authorized users to mark preprints as deleted.
    """
    template_name = 'preprints/remove_preprint.html'
    permission_required = ('osf.view_preprint', 'osf.delete_preprint')

    def post(self, request, *args, **kwargs):
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
    """ Allows authorized users to view list of withdraw requests for preprints and approve or reject the submitted
    preprint withdraw requests.
    """
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
            machine_state='initial',
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
        data = dict(request.POST)
        action = data.pop('action')[0]
        data.pop('csrfmiddlewaretoken', None)
        request_ids = list(data.keys())
        withdrawal_requests = PreprintRequest.objects.filter(id__in=request_ids)

        if action == 'reject':
            for withdrawal_request in withdrawal_requests:
                withdrawal_request.run_reject(self.request.user, withdrawal_request.comment)
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=withdrawal_request.id,
                    object_repr='PreprintRequest',
                    message=f'Approved withdrawal request: {withdrawal_request.id} of preprint {withdrawal_request.target._id}',
                    action_flag=APPROVE_WITHDRAWAL
                )

        if action == 'approve':
            for withdrawal_request in withdrawal_requests:
                withdrawal_request.run_accept(self.request.user, withdrawal_request.comment)
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=withdrawal_request.id,
                    object_repr='PreprintRequest',
                    message=f'Rejected withdrawal request: {withdrawal_request.id} of preprint {withdrawal_request.target._id}',
                    action_flag=REJECT_WITHDRAWAL
                )

        return redirect('preprints:withdrawal-requests')


class WithdrawalRequestMixin(PermissionRequiredMixin):
    permission_required = 'osf.change_preprintrequest'

    def get_object(self):
        return PreprintRequest.objects.filter(
            request_type='withdrawal',
            target__guids___id=self.kwargs['guid'],
        ).first()

    def get_success_url(self):
        return reverse_lazy('preprints:withdrawal-requests')


class PreprintApproveWithdrawalRequest(WithdrawalRequestMixin, View):
    """ Allows authorized users to approve withdraw requests for preprints, withdrawing/retracting them.
    """

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
    """ Allows authorized users to reject withdraw requests for preprints, sending them into the `pending` state.
    """

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


class PreprintFlaggedSpamList(PreprintSpamList, View):
    """ Allows authorized users to view a list of preprints flagged as spam.
    """
    SPAM_STATE = SpamStatus.FLAGGED
    template_name = 'preprints/flagged_spam_list.html'

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.mark_spam'):
            raise PermissionDenied("You don't have permission to update this user's spam status.")

        data = dict(request.POST)
        action = data.pop('action')[0]
        data.pop('csrfmiddlewaretoken', None)
        preprints = Preprint.objects.filter(id__in=list(data))

        if action == 'spam':
            for preprint in preprints:
                preprint.confirm_spam(save=True)
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=preprint.id,
                    object_repr='Node',
                    message=f'Confirmed SPAM: {preprint.id}',
                    action_flag=CONFIRM_SPAM
                )

                if preprint.get_identifier_value('doi'):
                    preprint.request_identifier_update(category='doi')

        if action == 'ham':
            for preprint in preprints:
                preprint.confirm_ham(save=True)
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=preprint.id,
                    object_repr='User',
                    message=f'Confirmed HAM: {preprint.id}',
                    action_flag=CONFIRM_HAM
                )

                if preprint.get_identifier_value('doi'):
                    preprint.request_identifier_update(category='doi')

        if action == 'unflag':
            for preprint in preprints:
                preprint.spam_status = None
                preprint.save()
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=preprint.id,
                    object_repr='User',
                    message=f'Confirmed HAM: {preprint.id}',
                    action_flag=CONFIRM_HAM
                )

                if preprint.get_identifier_value('doi'):
                    preprint.request_identifier_update(category='doi')

        return redirect('preprints:flagged-spam')


class PreprintKnownSpamList(PreprintSpamList):
    """ Allows authorized users to view a list of preprints marked as spam.
    """

    SPAM_STATE = SpamStatus.SPAM
    template_name = 'preprints/known_spam_list.html'


class PreprintKnownHamList(PreprintSpamList):
    """ Allows authorized users to view a list of preprints marked as ham.
    """
    SPAM_STATE = SpamStatus.HAM
    template_name = 'preprints/known_spam_list.html'


class PreprintConfirmSpamView(PreprintMixin, View):
    """ Allows authorized users to mark preprints as spam.
    """
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

        return redirect(self.get_success_url())


class PreprintConfirmHamView(PreprintMixin, View):
    """ Allows authorized users to mark preprints as ham.
    """
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

        return redirect(self.get_success_url())


class PreprintConfirmUnflagView(PreprintMixin, View):
    """ Allows authorized users to remove the spam flag from a preprint.
    """
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.spam_status = None
        preprint.save()
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Node',
            message=f'Confirmed Unflagged: {preprint._id}',
            action_flag=UNFLAG_SPAM
        )
        return redirect(self.get_success_url())


class PreprintMakePrivate(PreprintMixin, View):
    """ Allows an authorized user to manually make a public preprint private.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()

        preprint.set_privacy('private', force=True)
        preprint.save()

        return redirect(self.get_success_url())


class PreprintMakePublic(PreprintMixin, View):
    """ Allows an authorized user to manually make a private preprint public.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        try:
            preprint.set_privacy('public')
            preprint.save()
        except PreprintStateError as e:
            messages.error(self.request, str(e))

        return redirect(self.get_success_url())
