import pytz
from enum import Enum
from datetime import datetime
from framework import status

from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import NoReverseMatch
from django.db.models import F, Case, When, IntegerField
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.views.generic import (
    View,
    FormView,
    ListView,
)
from django.shortcuts import redirect, reverse, get_object_or_404
from django.urls import reverse_lazy

from admin.base.utils import change_embargo_date
from admin.base.views import GuidView
from admin.base.forms import GuidForm
from admin.notifications.views import detect_duplicate_notifications, delete_selected_notifications

from api.share.utils import update_share
from api.caching.tasks import update_storage_usage_cache

from osf.exceptions import NodeStateError, RegistrationStuckError
from osf.management.commands.change_node_region import _update_schema_meta
from osf.models import (
    Guid,
    OSFUser,
    NodeLog,
    AbstractNode,
    Registration,
    RegistrationProvider,
    RegistrationApproval,
    SpamStatus,
    TrashedFile
)
from osf.models.admin_log_entry import (
    update_admin_log,
    NODE_REMOVED,
    NODE_RESTORED,
    CONTRIBUTOR_REMOVED,
    CONFIRM_SPAM,
    CONFIRM_HAM,
    UNFLAG_SPAM,
    REINDEX_SHARE,
    REINDEX_ELASTIC,
)
from osf.utils.permissions import ADMIN

from scripts.approve_registrations import approve_past_pendings

from website import settings, search


class NodeMixin(PermissionRequiredMixin):

    def get_object(self):
        return AbstractNode.objects.filter(
            guids___id=self.kwargs['guid']
        ).annotate(
            guid=F('guids___id'),
            public_cap=Case(
                When(
                    custom_storage_usage_limit_public=None,
                    then=settings.STORAGE_LIMIT_PUBLIC,
                ),
                When(
                    custom_storage_usage_limit_public__gt=0,
                    then=F('custom_storage_usage_limit_public'),
                ),
                output_field=IntegerField()
            ),
            private_cap=Case(
                When(
                    custom_storage_usage_limit_private=None,
                    then=settings.STORAGE_LIMIT_PRIVATE,
                ),
                When(
                    custom_storage_usage_limit_private__gt=0,
                    then=F('custom_storage_usage_limit_private'),
                ),
                output_field=IntegerField()
            )
        ).get()

    def get_success_url(self):
        return reverse('nodes:node', kwargs={'guid': self.kwargs['guid']})


class NodeView(NodeMixin, GuidView):
    """ Allows authorized users to view node info.
    """
    template_name = 'nodes/node.html'
    permission_required = 'osf.view_node'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        node = self.get_object()

        detailed_duplicates = detect_duplicate_notifications(node_id=node.id)
        children = node.get_nodes(is_node_link=False)
        # Annotate guid because django templates prohibit accessing attributes that start with underscores
        children = AbstractNode.objects.filter(
            id__in=[child.id for child in children]
        ).prefetch_related('guids').annotate(guid=F('guids___id'))
        context.update({
            'SPAM_STATUS': SpamStatus,
            'STORAGE_LIMITS': settings.StorageLimits,
            'node': node,
            'children': children,
            'duplicates': detailed_duplicates
        })

        return context

class NodeRemoveNotificationView(View):
    def post(self, request, *args, **kwargs):
        selected_ids = request.POST.getlist('selected_notifications')
        if selected_ids:
            delete_selected_notifications(selected_ids)
            messages.success(request, 'Selected notifications were successfully deleted.')
        else:
            messages.error(request, 'No notifications selected for deletion.')

        return redirect('nodes:node', guid=kwargs.get('guid'))


class NodeUpdateModerationStateView(View):
    def post(self, request, *args, **kwargs):
        guid = kwargs.get('guid')
        node = AbstractNode.load(guid)
        node.update_moderation_state()
        messages.success(request, 'Moderation state successfully updated.')

        return redirect('nodes:node', guid=kwargs.get('guid'))


class NodeSearchView(PermissionRequiredMixin, FormView):
    """ Allows authorized users to search for a node by it's guid.
    """
    template_name = 'nodes/search.html'
    permission_required = 'osf.view_node'
    raise_exception = True
    form_class = GuidForm
    success_url = reverse_lazy('nodes:search')

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        if guid:
            try:
                return redirect(reverse('nodes:node', kwargs={'guid': guid}))
            except NoReverseMatch as e:
                messages.error(self.request, str(e))

        return super().form_valid(form)


class NodeRemoveContributorView(NodeMixin, View):
    """ Allows authorized users to remove contributors from nodes.
    """
    permission_required = ('osf.view_node', 'osf.change_node')
    raise_exception = True

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        user = OSFUser.objects.get(id=self.kwargs.get('user_id'))
        if node.has_permission(user, ADMIN) and not node._get_admin_contributors_query(node._contributors.all(), require_active=False).exclude(user=user).exists():
            messages.error(self.request, 'Must be at least one admin on this node.')
            return redirect(self.get_success_url())

        if node.remove_contributor(user, None, log=False, _force=True):
            update_admin_log(
                user_id=self.request.user.id,
                object_id=node.pk,
                object_repr='Contributor',
                message=f'User {user.pk} removed from {node.__class__.__name__.lower()} {node.pk}.',
                action_flag=CONTRIBUTOR_REMOVED
            )
            # Log invisibly on the OSF.
            self.add_contributor_removed_log(node, user)
        return redirect(self.get_success_url())

    def add_contributor_removed_log(self, node, user):
        NodeLog(
            action=NodeLog.CONTRIB_REMOVED,
            user=None,
            params={
                'project': node.parent_id,
                'node': node.pk,
                'contributors': user.pk
            },
            date=timezone.now(),
            should_hide=True,
        ).save()


class NodeDeleteView(NodeMixin, View):
    """ Allows authorized users to mark nodes as deleted.
    """
    permission_required = ('osf.view_node', 'osf.delete_node')
    raise_exception = True

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        if node.is_deleted:
            node.is_deleted = False
            node.deleted_date = None
            node.deleted = None
            update_admin_log(
                user_id=self.request.user.id,
                object_id=node.pk,
                object_repr='Node',
                message=f'Node {node.pk} restored.',
                action_flag=NODE_RESTORED
            )
            NodeLog(
                action=NodeLog.NODE_CREATED,
                user=None,
                params={
                    'project': node.parent_id,
                },
                date=timezone.now(),
                should_hide=True,
            ).save()
        else:
            node.is_deleted = True
            node.deleted = timezone.now()
            node.deleted_date = node.deleted
            update_admin_log(
                user_id=self.request.user.id,
                object_id=node.pk,
                object_repr='Node',
                message=f'Node {node.pk} removed.',
                action_flag=NODE_REMOVED
            )
            NodeLog(
                action=NodeLog.NODE_REMOVED,
                user=None,
                params={
                    'project': node.parent_id,
                },
                date=timezone.now(),
                should_hide=True,
            ).save()
        node.save()

        return redirect(self.get_success_url())


class AdminNodeLogView(NodeMixin, ListView):
    """ Allows authorized users to view node logs.
    """
    template_name = 'nodes/node_logs.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date'
    permission_required = 'osf.view_node'
    raise_exception = True

    def get_queryset(self):
        return self.get_object().logs.order_by('created')

    def get_context_data(self, **kwargs):
        query_set = self.get_queryset()
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)

        return {
            'logs': query_set,
            'page': page,
        }


class AdminNodeSchemaResponseView(NodeMixin, ListView):
    """ Allows authorized users to view schema response info.
    """
    template_name = 'schema_response/schema_response_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date'
    permission_required = 'osf.view_schema_response'
    raise_exception = True

    def get_queryset(self):
        return self.get_object().schema_responses.all()

    def get_context_data(self, **kwargs):
        return {'schema_responses': self.get_queryset()}


class RegistrationListView(PermissionRequiredMixin, ListView):
    """ Allow authorized users to view the list of registrations of a node.
    """
    template_name = 'nodes/registration_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'created'
    permission_required = 'osf.view_registration'
    raise_exception = True

    def get_queryset(self):
        # Django template does not like attributes with underscores for some reason, so we annotate.
        return Registration.objects.all().annotate(guid=F('guids___id')).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = self.get_queryset()
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        return {
            'nodes': query_set,
            'page': page,
        }


class StuckRegistrationListView(RegistrationListView):
    """ Allows authorized users to view a list of registrations the have been archiving files by more then 24 hours.
    """

    def get_queryset(self):
        # Django template does not like attributes with underscores for some reason, so we annotate.
        return Registration.find_failed_registrations().annotate(guid=F('guids___id'))


class RegistrationBacklogListView(RegistrationListView):
    """ List view that filters by registrations the haven't been archived at archive.org/
    """

    def get_queryset(self):
        # Django template does not like attributes with underscores for some reason, so we annotate.
        return Registration.find_ia_backlog().annotate(guid=F('guids___id'))


class DoiBacklogListView(RegistrationListView):
    """ Allows authorized users to view a list of registrations that have not yet been assigned a doi.
    """

    def get_queryset(self):
        # Django template does not like attributes with underscores for some reason, so we annotate.
        return Registration.find_doi_backlog().annotate(guid=F('guids___id'))


class ApprovalBacklogListView(RegistrationListView):
    """ Allows authorized users to view a list of registrations that have not yet been approved.
    """
    template_name = 'nodes/registration_approval_list.html'
    permission_required = 'osf.view_registrationapproval'

    def get_queryset(self):
        # Django template does not like attributes with underscores for some reason, so we annotate.
        return RegistrationApproval.find_approval_backlog()

    def get_context_data(self, **kwargs):
        queryset = self.get_queryset()
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
        return {
            'queryset': queryset,
            'page': page,
        }


class ConfirmApproveBacklogView(RegistrationListView):
    template_name = 'nodes/registration_approval_list.html'
    permission_required = 'osf.view_registrationapproval'

    def get_success_url(self):
        return reverse('nodes:approval-backlog-list')

    def post(self, request, *args, **kwargs):
        data = dict(request.POST)
        data.pop('csrfmiddlewaretoken', None)
        approvals = RegistrationApproval.objects.filter(_id__in=list(data.keys()))
        approve_past_pendings(approvals, dry_run=False)
        return redirect(self.get_success_url())


class RegistrationUpdateEmbargoView(NodeMixin, View):
    """ Allows authorized users to update the embargo of a registration.
    """
    permission_required = ('osf.change_node')
    raise_exception = True

    def post(self, request, *args, **kwargs):
        end_date = request.POST.get('date')
        user = request.user
        registration = self.get_object()

        try:
            end_date = pytz.utc.localize(datetime.strptime(end_date, '%m/%d/%Y'))
            change_embargo_date(registration, user, end_date)
        except ValueError:
            return HttpResponse('Please enter a valid date.', status=400)
        except ValidationError as e:
            return HttpResponse(e, status=400)
        except PermissionDenied as e:
            return HttpResponse(e, status=403)

        return redirect(self.get_success_url())


class RegistrationChangeProviderView(NodeMixin, View):
    """ Allows authorized users to update provider of a registration.
    """
    permission_required = ('osf.change_node')

    def post(self, request, *args, **kwargs):
        provider_id = int(request.POST.get('provider_id'))
        provider = get_object_or_404(RegistrationProvider, pk=provider_id)
        registration = self.get_object()

        try:
            provider.validate_schema(registration.registration_schema)
            registration.provider = provider
            registration.save()
        except ValidationError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Provider successfully changed.')

        return redirect(self.get_success_url())


class NodeSpamList(PermissionRequiredMixin, ListView):
    """ Allows authorized users to view a list of nodes that have a particular spam status.
    """
    SPAM_STATE = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = 'created'
    permission_required = 'osf.view_spam'
    raise_exception = True

    def get_queryset(self):
        return AbstractNode.objects.filter(
            spam_status=self.SPAM_STATE
        ).order_by(
            self.ordering
        ).annotate(guid=F('guids___id'))

    def get_context_data(self, **kwargs):
        query_set = self.get_queryset()
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        return {'nodes': query_set, 'page': page}


class NodeFlaggedSpamList(NodeSpamList, View):
    """ Allows authorized users to mark users flagged as spam as either spam or ham, or they can simply remove the flag.
    """
    template_name = 'nodes/flagged_spam_list.html'
    SPAM_STATE = SpamStatus.FLAGGED

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.mark_spam'):
            raise PermissionDenied("You don't have permission to update this user's spam status.")

        data = dict(request.POST)
        action = data.pop('action')[0]
        data.pop('csrfmiddlewaretoken', None)
        nodes = AbstractNode.objects.filter(id__in=list(data.keys()))

        if action == 'spam':
            for node in nodes:
                try:
                    node.confirm_spam(save=True)
                    update_admin_log(
                        user_id=self.request.user.id,
                        object_id=node.id,
                        object_repr='Node',
                        message=f'Confirmed SPAM: {node._id}',
                        action_flag=CONFIRM_SPAM
                    )
                except NodeStateError as e:
                    messages.error(self.request, e)

        if action == 'ham':
            for node in nodes:
                node.confirm_ham(save=True)
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=node.id,
                    object_repr='User',
                    message=f'Confirmed HAM: {node._id}',
                    action_flag=CONFIRM_HAM
                )

        if action == 'unflag':
            for node in nodes:
                node.spam_status = None
                node.save()
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=node._id,
                    object_repr='Node',
                    message=f'Confirmed Unflagged: {node._id}',
                    action_flag=UNFLAG_SPAM
                )

        for node in nodes:
            if node.get_identifier_value('doi'):
                node.request_identifier_update(category='doi')

        return redirect('nodes:flagged-spam')


class NodeKnownSpamList(NodeSpamList):
    """ Allows authorized users to view a list of users that have a spam status of being spam.
    """
    template_name = 'nodes/known_spam_list.html'

    SPAM_STATE = SpamStatus.SPAM


class NodeKnownHamList(NodeSpamList):
    """ Allows authorized users to view a list of users that have a spam status of being ham (non-spam).
    """
    template_name = 'nodes/known_spam_list.html'
    SPAM_STATE = SpamStatus.HAM


class NodeConfirmSpamView(NodeMixin, View):
    """ Allows authorized users to mark a particular node as spam.
    """
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        node.confirm_spam(save=True)

        if node.get_identifier_value('doi'):
            node.request_identifier_update(category='doi')

        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message=f'Confirmed SPAM: {node._id}',
            action_flag=CONFIRM_SPAM
        )
        return redirect(self.get_success_url())


class NodeConfirmHamView(NodeMixin, View):
    """ Allows authorized users to mark a particular node as ham.
    """
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        node.confirm_ham(save=True)

        if node.get_identifier_value('doi'):
            node.request_identifier_update(category='doi')

        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message=f'Confirmed HAM: {node._id}',
            action_flag=CONFIRM_HAM
        )
        return redirect(self.get_success_url())


class NodeConfirmUnflagView(NodeMixin, View):
    """ Allows authorized users to remove the spam flag from a node.
    """
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        node.spam_status = None
        node.save()
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message=f'Confirmed Unflagged: {node._id}',
            action_flag=UNFLAG_SPAM
        )
        return redirect(self.get_success_url())


class NodeReindexShare(NodeMixin, View):
    """ Allows an authorized user to reindex a node in SHARE.
    """
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        update_share(node)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message=f'Node Reindexed (SHARE): {node._id}',
            action_flag=REINDEX_SHARE
        )
        return redirect(self.get_success_url())


class NodeReindexElastic(NodeMixin, View):
    """ Allows an authorized user to reindex a node in ElasticSearch.
    """
    permission_required = 'osf.mark_spam'

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        search.search.update_node(node, bulk=False, async_update=False)

        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message=f'Node Reindexed (Elastic): {node._id}',
            action_flag=REINDEX_ELASTIC
        )
        return redirect(self.get_success_url())


class NodeModifyStorageUsage(NodeMixin, View):
    """ Allows an authorized user to view a node's storage usage info and set their public/private storage cap.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        new_private_cap = request.POST.get('private-cap-input')
        new_public_cap = request.POST.get('public-cap-input')

        node_private_cap = node.custom_storage_usage_limit_private or settings.STORAGE_LIMIT_PRIVATE
        node_public_cap = node.custom_storage_usage_limit_public or settings.STORAGE_LIMIT_PUBLIC

        if float(new_private_cap) != node_private_cap:
            node.custom_storage_usage_limit_private = new_private_cap

        if float(new_public_cap) != node_public_cap:
            node.custom_storage_usage_limit_public = new_public_cap

        node.save()
        return redirect(self.get_success_url())


class NodeRecalculateStorage(NodeMixin, View):
    """ Allows an authorized user to manually set a node's storage cache by recalculating the value.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        update_storage_usage_cache(node.id, node._id)
        return redirect(self.get_success_url())


class NodeMakePrivate(NodeMixin, View):
    """ Allows an authorized user to manually make a public node private.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        node = self.get_object()

        node.is_public = False

        # After set permissions callback
        for addon in node.get_addons():
            message = addon.after_set_privacy(node, 'private')
            if message:
                status.push_status_message(message, kind='info', trust=False)

        if node.get_identifier_value('doi'):
            node.request_identifier_update(category='doi')

        node.save()

        return redirect(self.get_success_url())


class NodeMakePublic(NodeMixin, View):
    """ Allows an authorized user to manually make a public node private.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        try:
            node.set_privacy('public')
        except NodeStateError as e:
            messages.error(request, str(e))
        return redirect(self.get_success_url())


class NodeRemoveFileView(NodeMixin, View):
    """ Allows an authorized user to remove file from node.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        node = self.get_object()
        guid_id = request.POST.get('remove-file-guid', '').strip()
        guid = Guid.load(guid_id)
        if guid and (file := guid.referent) and (node.registered_from == file.target) and not isinstance(file, TrashedFile):
            file.delete()
            _update_schema_meta(file.target)
        return redirect(self.get_success_url())


class RemoveStuckRegistrationsView(NodeMixin, View):
    """ Allows an authorized user to remove a registrations if it's stuck in the archiving process.
    """
    permission_required = ('osf.view_node', 'osf.change_node')

    def post(self, request, *args, **kwargs):
        stuck_reg = self.get_object()
        if Registration.find_failed_registrations().filter(id=stuck_reg.id).exists():
            stuck_reg.delete_registration_tree(save=True)
            messages.success(request, 'The registration has been deleted')
        else:
            messages.error(request, 'This registration may not technically be stuck,'
                                    ' if the problem persists get a developer to fix it.')

        return redirect(self.get_success_url())


class CheckArchiveStatusRegistrationsView(NodeMixin, View):
    """Allows an authorized user to check a registration archive status.
    """
    permission_required = ('osf.view_node', 'osf.change_node')

    def get(self, request, *args, **kwargs):
        # Prevents circular imports that cause admin app to hang at startup
        from osf.management.commands.force_archive import check

        registration = self.get_object()

        if registration.archived:
            messages.success(request, f"Registration {registration._id} is archived.")
            return redirect(self.get_success_url())

        try:
            archive_status = check(registration)
            messages.success(request, archive_status)
        except RegistrationStuckError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_success_url())


class CollisionMode(Enum):
    NONE: str = 'none'
    SKIP: str = 'skip'
    DELETE: str = 'delete'


class ForceArchiveRegistrationsView(NodeMixin, View):
    """Allows an authorized user to force archive registration.
    """
    permission_required = ('osf.view_node', 'osf.change_node')

    def post(self, request, *args, **kwargs):
        # Prevents circular imports that cause admin app to hang at startup
        from osf.management.commands.force_archive import verify, archive, DEFAULT_PERMISSIBLE_ADDONS

        registration = self.get_object()
        force_archive_params = request.POST

        collision_mode = force_archive_params.get('collision_mode', CollisionMode.NONE.value)
        delete_collision = CollisionMode.DELETE.value == collision_mode
        skip_collision = CollisionMode.SKIP.value == collision_mode

        allow_unconfigured = force_archive_params.get('allow_unconfigured', False)

        addons = set(registration.registered_from.get_addon_names())
        addons.update(DEFAULT_PERMISSIBLE_ADDONS)

        try:
            verify(registration, permissible_addons=addons, raise_error=True)
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect(self.get_success_url())

        dry_mode = force_archive_params.get('dry_mode', False)

        if dry_mode:
            messages.success(request, f"Registration {registration._id} can be archived.")
        else:
            try:
                archive(
                    registration,
                    permissible_addons=addons,
                    allow_unconfigured=allow_unconfigured,
                    skip_collisions=skip_collision,
                    delete_collisions=delete_collision,
                )
                messages.success(request, 'Registration archive process has finished.')
            except Exception as exc:
                messages.error(request, f'This registration cannot be archived due to {exc.__class__.__name__}: {str(exc)}. '
                                        f'If the problem persists get a developer to fix it.')

        return redirect(self.get_success_url())


class NodeResyncDataCiteView(NodeMixin, View):
    """ Allows an authorized user to run resync with DataCite for a single registration object.
    """
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        registration = self.get_object()
        registration.request_identifier_update('doi', create=True)
        return redirect(self.get_success_url())


class NodeRevertToDraft(NodeMixin, View):
    permission_required = 'osf.change_node'

    def post(self, request, *args, **kwargs):
        registration = self.get_object()
        registration.to_draft()
        return redirect(self.get_success_url())
