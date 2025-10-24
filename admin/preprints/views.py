from django.db import transaction
from django.db.models import F
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import (
    View,
    ListView,
    FormView,
)
from django.utils import timezone
from django.urls import NoReverseMatch, reverse_lazy

from admin.base.views import GuidView
from admin.base.forms import GuidForm
from admin.nodes.views import NodeRemoveContributorView
from admin.preprints.forms import ChangeProviderForm, MachineStateForm
from admin.base.utils import osf_staff_check

from api.share.utils import update_share
from api.providers.workflows import Workflows
from api.preprints.serializers import PreprintSerializer

from osf.exceptions import PreprintStateError
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied
from framework.exceptions import PermissionsError

from osf.management.commands.fix_preprints_has_data_links_and_why_no_data import process_wrong_why_not_data_preprints
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
from osf.utils.workflows import DefaultStates
from website import search
from website.files.utils import copy_files
from website.preprints.tasks import on_preprint_updated


class PreprintMixin(PermissionRequiredMixin):

    def get_object(self):
        preprint = Preprint.load(self.kwargs['guid'])
        # Django template does not like attributes with underscores for some reason
        preprint.guid = preprint._id
        return preprint

    def get_success_url(self, guid=None):
        return reverse_lazy('preprints:preprint', kwargs={'guid': guid or self.kwargs['guid']})


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
        new_machine_state = request.POST.get('machine_state')
        if new_machine_state and preprint.machine_state != new_machine_state:
            preprint.machine_state = new_machine_state
            try:
                preprint.save()
            except Exception as e:
                messages.error(self.request, e.message)

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


class PreprintReVersion(PreprintMixin, View):
    """Allows an authorized user to create new version 1 of a preprint based on earlier
    primary file version(s). All operations are executed within an atomic transaction.
    If any step fails, the entire transaction will be rolled back and no version will be changed.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()

        file_versions = request.POST.getlist('file_versions')
        if not file_versions:
            return HttpResponse('At least one file version should be attached.', status=400)

        try:
            with transaction.atomic():
                versions = preprint.get_preprint_versions()
                for version in versions:
                    version.upgrade_version()

                new_preprint, data_to_update = Preprint.create_version(
                    create_from_guid=preprint._id,
                    assign_version_number=1,
                    auth=request,
                    ignore_permission=True,
                    ignore_existing_versions=True,
                )
                data_to_update = data_to_update or dict()

                primary_file = copy_files(preprint.primary_file, target_node=new_preprint, identifier__in=file_versions)
                if primary_file is None:
                    raise ValueError(f"Primary file {preprint.primary_file.id} doesn't have following versions: {file_versions}")  # rollback changes
                data_to_update['primary_file'] = primary_file

                # FIXME: currently it's not possible to ignore permission when update subjects
                # via serializer, remove this logic if deprecated
                subjects = data_to_update.pop('subjects', None)
                if subjects:
                    new_preprint.set_subjects_from_relationships(subjects, auth=request, ignore_permission=True)

                PreprintSerializer(new_preprint, context={'request': request, 'ignore_permission': True}).update(new_preprint, data_to_update)
        except ValueError as exc:
            return HttpResponse(str(exc), status=400)
        except (PermissionsError, DrfPermissionDenied) as exc:
            return HttpResponse(f'Not enough permissions to perform this action : {str(exc)}', status=400)

        return JsonResponse({'redirect': self.get_success_url(new_preprint._id)})


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


class PreprintHardDeleteView(PreprintMixin, View):
    """Allows authorized users to permanently delete an initial-state preprint version.

    This removes ONLY the broken draft preprint version (N+1) and its GuidVersionsThrough
    version record, preserving all previous good versions (1 through N) so that a user
    can initiate a new version again.

    Based on create_version() and check_unfinished_or_unpublished_version() logic:
    - Each version is a separate preprint instance
    - The base Guid points to the latest published version
    - We only delete the specific broken draft version, not the entire preprint lineage
    """
    permission_required = ('osf.delete_preprint',)

    def post(self, request, *args, **kwargs):
        if not osf_staff_check(request.user):
            messages.error(request, 'Only staff can perform hard deletes.')
            return redirect(self.get_success_url())

        preprint = self.get_object()

        if preprint.machine_state != DefaultStates.INITIAL.value:
            messages.error(request, f'Only initial-state drafts can be hard deleted. Current state: {preprint.machine_state}')
            return redirect(self.get_success_url())

        try:
            with transaction.atomic():
                guid_version = preprint.versioned_guids.first()
                if not guid_version:
                    messages.error(request, 'No version record found for this draft preprint')
                    return redirect('preprints:search')

                version_number = guid_version.version
                base_guid_obj = guid_version.guid

                previous_version = base_guid_obj.versions.filter(
                    version__lt=version_number,
                    is_rejected=False
                ).order_by('-version').first()
                if previous_version:
                    base_guid_obj.referent = previous_version.referent
                    base_guid_obj.object_id = previous_version.object_id
                    base_guid_obj.content_type = previous_version.content_type
                    base_guid_obj.save()

                guid_version.delete()
                preprint.delete()

            messages.success(request, f'Successfully deleted draft version {version_number}. Previous versions preserved.')
            return redirect('preprints:search')
        except Exception as exc:
            messages.error(request, f'Failed to hard delete draft preprint: {str(exc)}')
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
        target = Preprint.load(self.kwargs['guid'])
        return PreprintRequest.objects.filter(
            request_type='withdrawal',
            target=target,
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

class PreprintFixEditing(PreprintMixin, View):
    """ Allows an authorized user to manually fix why not data field.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        process_wrong_why_not_data_preprints(
            version_guid=preprint._id,
            dry_run=False,
            executing_through_command=False,
        )

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


class PreprintResyncCrossRefView(PreprintMixin, View):
    """ Allows an authorized user to run resync with CrossRef for a single object.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.request_identifier_update('doi', create=True)
        return redirect(self.get_success_url())


class PreprintMakePublishedView(PreprintMixin, View):
    """ Allows an authorized user to make a preprint published.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()
        preprint.set_published(
            published=True,
            auth=request,
            save=True,
            ignore_permission=True
        )
        if preprint.provider and preprint.provider.reviews_workflow == Workflows.POST_MODERATION.value:
            on_preprint_updated.apply_async(kwargs={'preprint_id': preprint._id})

        return redirect(self.get_success_url())

class PreprintUnwithdrawView(PreprintMixin, View):
    """ Allows authorized users to unwithdraw a preprint that was previously withdrawn.
    """
    permission_required = ('osf.change_node')

    def post(self, request, *args, **kwargs):
        preprint = self.get_object()

        if preprint.machine_state != 'withdrawn':
            messages.error(request, f'Preprint {preprint._id} is not withdrawn')
            return redirect(self.get_success_url())

        withdraw_action = preprint.actions.filter(to_state='withdrawn').last()
        last_action = preprint.actions.last()

        preprint.withdrawal_justification = ''
        preprint.date_withdrawn = None

        if withdraw_action:
            preprint.machine_state = withdraw_action.from_state
            withdraw_action.delete()
        else:
            if last_action:
                preprint.machine_state = last_action.to_state
            else:
                # Default to put it back in moderation if we don't know where it came from
                preprint.machine_state = 'pending'

        from osf.utils.migrations import disable_auto_now_fields
        with disable_auto_now_fields():
            req = preprint.requests.filter(machine_state=DefaultStates.ACCEPTED.value).first()
            if req:
                req.delete()

            preprint.save()
        return redirect(self.get_success_url())
