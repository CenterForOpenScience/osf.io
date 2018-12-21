from __future__ import unicode_literals

import pytz
from datetime import datetime

from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.generic import ListView, DeleteView, View, TemplateView
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.db.models import Q

from website import search
from osf.models import NodeLog
from osf.models.user import OSFUser
from osf.models.node import Node
from osf.models.registrations import Registration
from osf.models import SpamStatus
from admin.base.utils import change_embargo_date, validate_embargo_date
from admin.base.views import GuidFormView, GuidView
from osf.models.admin_log_entry import (
    update_admin_log,
    NODE_REMOVED,
    NODE_RESTORED,
    CONTRIBUTOR_REMOVED,
    CONFIRM_SPAM,
    CONFIRM_HAM,
    REINDEX_SHARE,
    REINDEX_ELASTIC,
)
from admin.nodes.templatetags.node_extras import reverse_node
from admin.nodes.serializers import serialize_node, serialize_simple_user_and_node_permissions, serialize_log
from website.project.tasks import update_node_share
from website.project.views.register import osf_admin_change_status_identifier


class NodeFormView(PermissionRequiredMixin, GuidFormView):
    """ Allow authorized admin user to input specific node guid.

    Basic form. No admin models.
    """
    template_name = 'nodes/search.html'
    object_type = 'node'
    permission_required = 'osf.view_node'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_node(self.guid)


class NodeRemoveContributorView(PermissionRequiredMixin, DeleteView):
    """ Allow authorized admin user to remove project contributor

    Interface with OSF database. No admin models.
    """
    template_name = 'nodes/remove_contributor.html'
    context_object_name = 'node'
    permission_required = ('osf.view_node', 'osf.change_node')
    raise_exception = True

    def add_contributor_removed_log(self, node, user):
        osf_log = NodeLog(
            action=NodeLog.CONTRIB_REMOVED,
            user=None,
            params={
                'project': node.parent_id,
                'node': node.pk,
                'contributors': user.pk
            },
            date=timezone.now(),
            should_hide=True,
        )
        return osf_log.save()

    def delete(self, request, *args, **kwargs):
        try:
            node, user = self.get_object()
            if node.remove_contributor(user, None, log=False):
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=node.pk,
                    object_repr='Contributor',
                    message='User {} removed from {} {}.'.format(
                        user.pk, node.__class__.__name__.lower(), node.pk
                    ),
                    action_flag=CONTRIBUTOR_REMOVED
                )
                # Log invisibly on the OSF.
                self.add_contributor_removed_log(node, user)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        self.kwargs.get('guid')
                    )
                )
            )
        if isinstance(node, Node):
            return redirect(reverse_node(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        node, user = kwargs.get('object')
        context.setdefault('guid', node._id)
        context.setdefault('user', serialize_simple_user_and_node_permissions(node, user))
        context['link'] = 'nodes:remove_user'
        context['resource_type'] = 'project'
        return super(NodeRemoveContributorView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return (Node.load(self.kwargs.get('guid')),
                OSFUser.load(self.kwargs.get('user_id')))


class NodeDeleteBase(DeleteView):
    template_name = None
    context_object_name = 'node'
    object = None

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(NodeDeleteBase, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return Node.load(self.kwargs.get('guid')) or Registration.load(self.kwargs.get('guid'))


class NodeDeleteView(PermissionRequiredMixin, NodeDeleteBase):
    """ Allow authorized admin user to remove/hide nodes

    Interface with OSF database. No admin models.
    """
    template_name = 'nodes/remove_node.html'
    object = None
    permission_required = ('osf.view_node', 'osf.delete_node')
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super(NodeDeleteView, self).get_context_data(**kwargs)
        context['link'] = 'nodes:remove'
        context['resource_type'] = 'node'
        return context

    def delete(self, request, *args, **kwargs):
        try:
            node = self.get_object()
            flag = None
            osf_flag = None
            message = None
            if node.is_deleted:
                node.is_deleted = False
                node.deleted_date = None
                flag = NODE_RESTORED
                message = 'Node {} restored.'.format(node.pk)
                osf_flag = NodeLog.NODE_CREATED
            elif not node.is_registration:
                node.is_deleted = True
                node.deleted_date = timezone.now()
                flag = NODE_REMOVED
                message = 'Node {} removed.'.format(node.pk)
                osf_flag = NodeLog.NODE_REMOVED
            node.save()
            if flag is not None:
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=node.pk,
                    object_repr='Node',
                    message=message,
                    action_flag=flag
                )
            if osf_flag is not None:
                # Log invisibly on the OSF.
                osf_log = NodeLog(
                    action=osf_flag,
                    user=None,
                    params={
                        'project': node.parent_id,
                    },
                    date=timezone.now(),
                    should_hide=True,
                )
                osf_log.save()
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('guid')
                    )
                )
            )
        return redirect(reverse_node(self.kwargs.get('guid')))


class NodeView(PermissionRequiredMixin, GuidView):
    """ Allow authorized admin user to view nodes

    View of OSF database. No admin models.
    """
    template_name = 'nodes/node.html'
    context_object_name = 'node'
    permission_required = 'osf.view_node'
    raise_exception = True

    def get_context_data(self, **kwargs):
        kwargs = super(NodeView, self).get_context_data(**kwargs)
        kwargs.update({'SPAM_STATUS': SpamStatus})  # Pass spam status in to check against
        kwargs.update({'message': kwargs.get('message')})  # Pass spam status in to check against
        return kwargs

    def get_object(self, queryset=None):
        guid = self.kwargs.get('guid')
        node = Node.load(guid) or Registration.load(guid)
        return serialize_node(node)


class AdminNodeLogView(PermissionRequiredMixin, ListView):
    """ Allow admins to see logs"""

    template_name = 'nodes/node_logs.html'
    context_object_name = 'node'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date'
    permission_required = 'osf.view_node'
    raise_exception = True

    def get_object(self, queryset=None):
        return Node.load(self.kwargs.get('guid')) or Registration.load(self.kwargs.get('guid'))

    def get_queryset(self):
        node = self.get_object()
        query = Q(node_id__in=list(Node.objects.get_children(node).values_list('id', flat=True)) + [node.id])
        return NodeLog.objects.filter(query).order_by('-date').include(
            'node__guids', 'user__guids', 'original_node__guids', limit_includes=10
        )

    def get_context_data(self, **kwargs):
        query_set = self.get_queryset()
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'logs': list(map(serialize_log, query_set)),
            'page': page,
        }


class RegistrationListView(PermissionRequiredMixin, ListView):
    """ Allow authorized admin user to view list of registrations

    View of OSF database. No admin models.
    """
    template_name = 'nodes/registration_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'created'
    context_object_name = '-node'
    permission_required = 'osf.view_registration'
    raise_exception = True

    def get_queryset(self):
        return Registration.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'nodes': list(map(serialize_node, query_set)),
            'page': page,
        }


class StuckRegistrationListView(RegistrationListView):
    """ List view that filters by registrations the have been archiving files by more then 24 hours.
    """

    def get_queryset(self):
        return Registration.find_failed_registrations().order_by(self.ordering)


class RegistrationUpdateEmbargoView(PermissionRequiredMixin, View):
    """ Allow authorized admin user to update the embargo of a registration
    """
    permission_required = ('osf.change_node')
    raise_exception = True

    def post(self, request, *args, **kwargs):
        validation_only = (request.POST.get('validation_only', False) == 'True')
        end_date = request.POST.get('date')
        user = request.user
        registration = self.get_object()

        try:
            end_date = pytz.utc.localize(datetime.strptime(end_date, '%m/%d/%Y'))
        except ValueError:
            return HttpResponse('Please enter a valid date.', status=400)

        try:
            if validation_only:
                validate_embargo_date(registration, user, end_date)
            else:
                change_embargo_date(registration, user, end_date)
        except ValidationError as e:
            return HttpResponse(e, status=409)
        except PermissionDenied as e:
            return HttpResponse(e, status=403)

        return redirect(reverse_node(self.kwargs.get('guid')))

    def get_object(self, queryset=None):
        return Registration.load(self.kwargs.get('guid'))

class NodeSpamList(PermissionRequiredMixin, ListView):
    SPAM_STATE = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = 'created'
    context_object_name = '-node'
    permission_required = 'osf.view_spam'
    raise_exception = True

    def get_queryset(self):
        return Node.objects.filter(spam_status=self.SPAM_STATE).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'nodes': list(map(serialize_node, query_set)),
            'page': page,
        }

class NodeFlaggedSpamList(NodeSpamList, DeleteView):
    SPAM_STATE = SpamStatus.FLAGGED
    template_name = 'nodes/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm('auth.mark_spam'):
            raise PermissionDenied('You do not have permission to update a node flagged as spam.')
        node_ids = [
            nid for nid in request.POST.keys()
            if nid != 'csrfmiddlewaretoken'
        ]
        for nid in node_ids:
            node = Node.load(nid)
            osf_admin_change_status_identifier(node)
            node.confirm_spam(save=True)
            update_admin_log(
                user_id=self.request.user.id,
                object_id=nid,
                object_repr='Node',
                message='Confirmed SPAM: {}'.format(nid),
                action_flag=CONFIRM_SPAM
            )
        return redirect('nodes:flagged-spam')


class NodeKnownSpamList(NodeSpamList):
    SPAM_STATE = SpamStatus.SPAM
    template_name = 'nodes/known_spam_list.html'

class NodeKnownHamList(NodeSpamList):
    SPAM_STATE = SpamStatus.HAM
    template_name = 'nodes/known_spam_list.html'

class NodeConfirmSpamView(PermissionRequiredMixin, NodeDeleteBase):
    template_name = 'nodes/confirm_spam.html'
    permission_required = 'osf.mark_spam'
    raise_exception = True
    object_type = 'Node'

    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        osf_admin_change_status_identifier(node)
        node.confirm_spam(save=True)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr=self.object_type,
            message='Confirmed SPAM: {}'.format(node._id),
            action_flag=CONFIRM_SPAM
        )
        if isinstance(node, Node):
            return redirect(reverse_node(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = super(NodeConfirmSpamView, self).get_context_data(**kwargs)
        context['link'] = 'nodes:confirm-spam'
        context['resource_type'] = self.object_type.lower()
        return context


class NodeConfirmHamView(PermissionRequiredMixin, NodeDeleteBase):
    template_name = 'nodes/confirm_ham.html'
    permission_required = 'osf.mark_spam'
    raise_exception = True
    object_type = 'Node'

    def get_context_data(self, **kwargs):
        context = super(NodeConfirmHamView, self).get_context_data(**kwargs)
        context['link'] = 'nodes:confirm-ham'
        context['resource_type'] = self.object_type.lower()
        return context

    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        node.confirm_ham(save=True)
        osf_admin_change_status_identifier(node)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr=self.object_type,
            message='Confirmed HAM: {}'.format(node._id),
            action_flag=CONFIRM_HAM
        )
        if isinstance(node, Node):
            return redirect(reverse_node(self.kwargs.get('guid')))

class NodeReindexShare(PermissionRequiredMixin, NodeDeleteBase):
    template_name = 'nodes/reindex_node_share.html'
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def get_object(self, queryset=None):
        return Node.load(self.kwargs.get('guid')) or Registration.load(self.kwargs.get('guid'))

    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        update_node_share(node)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message='Node Reindexed (SHARE): {}'.format(node._id),
            action_flag=REINDEX_SHARE
        )
        if isinstance(node, Node):
            return redirect(reverse_node(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = super(NodeReindexShare, self).get_context_data(**kwargs)
        context['link'] = 'nodes:reindex-share-node'
        context['resource_type'] = 'node'
        return context

class NodeReindexElastic(PermissionRequiredMixin, NodeDeleteBase):
    template_name = 'nodes/reindex_node_elastic.html'
    permission_required = 'osf.mark_spam'
    raise_exception = True

    def get_object(self, queryset=None):
        return Node.load(self.kwargs.get('guid')) or Registration.load(self.kwargs.get('guid'))

    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        search.search.update_node(node, bulk=False, async_update=False)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message='Node Reindexed (Elastic): {}'.format(node._id),
            action_flag=REINDEX_ELASTIC
        )
        return redirect(reverse_node(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = super(NodeReindexElastic, self).get_context_data(**kwargs)
        context['link'] = 'nodes:reindex-elastic-node'
        context['resource_type'] = 'node'
        return context


class StuckRegistrationsView(PermissionRequiredMixin, TemplateView):
    permission_required = ('osf.view_node', 'osf.change_node')
    raise_exception = True
    context_object_name = 'node'

    def get_object(self, queryset=None):
        return Registration.load(self.kwargs.get('guid'))


class RestartStuckRegistrationsView(StuckRegistrationsView):
    template_name = 'nodes/restart_registrations_modal.html'

    def post(self, request, *args, **kwargs):
        # Prevents circular imports that cause admin app to hang at startup
        from osf.management.commands.force_archive import archive, verify
        stuck_reg = self.get_object()
        if verify(stuck_reg):
            try:
                archive(stuck_reg)
                messages.success(request, 'Registration archive processes has restarted')
            except Exception as exc:
                messages.error(request, 'This registration cannot be unstuck due to {} '
                                        'if the problem persists get a developer to fix it.'.format(exc.__class__.__name__))

        else:
            messages.error(request, 'This registration may not technically be stuck,'
                                    ' if the problem persists get a developer to fix it.')

        return redirect(reverse_node(self.kwargs.get('guid')))


class RemoveStuckRegistrationsView(StuckRegistrationsView):
    template_name = 'nodes/remove_registrations_modal.html'

    def post(self, request, *args, **kwargs):
        stuck_reg = self.get_object()
        if Registration.find_failed_registrations().filter(id=stuck_reg.id).exists():
            stuck_reg.delete_registration_tree(save=True)
            messages.success(request, 'The registration has been deleted')
        else:
            messages.error(request, 'This registration may not technically be stuck,'
                                    ' if the problem persists get a developer to fix it.')

        return redirect(reverse_node(self.kwargs.get('guid')))
