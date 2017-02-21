from __future__ import unicode_literals

from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, DeleteView
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from django.contrib.auth.mixins import PermissionRequiredMixin
from modularodm import Q

from website.models import NodeLog
from osf.models.user import OSFUser
from osf.models.node import Node
from osf.models.registrations import Registration
from admin.base.views import GuidFormView, GuidView
from osf.models.admin_log_entry import (
    update_admin_log,
    NODE_REMOVED,
    NODE_RESTORED,
    CONTRIBUTOR_REMOVED,
    CONFIRM_SPAM, CONFIRM_HAM)
from admin.nodes.templatetags.node_extras import reverse_node
from admin.nodes.serializers import serialize_node, serialize_simple_user_and_node_permissions
from website.project.spam.model import SpamStatus


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

    def delete(self, request, *args, **kwargs):
        try:
            node, user = self.get_object()
            if node.remove_contributor(user, None, log=False):
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=node.pk,
                    object_repr='Contributor',
                    message='User {} removed from node {}.'.format(
                        user.pk, node.pk
                    ),
                    action_flag=CONTRIBUTOR_REMOVED
                )
                # Log invisibly on the OSF.
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
                osf_log.save()
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('node_id')
                    )
                )
            )
        return redirect(reverse_node(self.kwargs.get('node_id')))

    def get_context_data(self, **kwargs):
        context = {}
        node, user = kwargs.get('object')
        context.setdefault('node_id', node._id)
        context.setdefault('user', serialize_simple_user_and_node_permissions(node, user))
        return super(NodeRemoveContributorView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return (Node.load(self.kwargs.get('node_id')),
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
        return Node.load(self.kwargs.get('guid'))


class NodeDeleteView(PermissionRequiredMixin, NodeDeleteBase):
    """ Allow authorized admin user to remove/hide nodes

    Interface with OSF database. No admin models.
    """
    template_name = 'nodes/remove_node.html'
    object = None
    permission_required = ('osf.view_node', 'osf.delete_node')
    raise_exception = True

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
        return kwargs

    def get_object(self, queryset=None):
        return serialize_node(Node.load(self.kwargs.get('guid')))


class RegistrationListView(PermissionRequiredMixin, ListView):
    """ Allow authorized admin user to view list of registrations

    View of OSF database. No admin models.
    """
    template_name = 'nodes/registration_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date_created'
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
            'nodes': map(serialize_node, query_set),
            'page': page,
        }


class NodeSpamList(PermissionRequiredMixin, ListView):
    SPAM_STATE = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = 'date_created'
    context_object_name = '-node'
    permission_required = 'common_auth.view_spam'
    raise_exception = True

    def get_queryset(self):
        query = (
            Q('spam_status', 'eq', self.SPAM_STATE)
        )
        return Node.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'nodes': map(serialize_node, query_set),
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
    permission_required = 'common_auth.mark_spam'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        node.confirm_spam(save=True)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message='Confirmed SPAM: {}'.format(node._id),
            action_flag=CONFIRM_SPAM
        )
        return redirect(reverse_node(self.kwargs.get('guid')))

class NodeConfirmHamView(PermissionRequiredMixin, NodeDeleteBase):
    template_name = 'nodes/confirm_ham.html'
    permission_required = 'common_auth.mark_spam'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        node.confirm_ham(save=True)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=node._id,
            object_repr='Node',
            message='Confirmed HAM: {}'.format(node._id),
            action_flag=CONFIRM_HAM
        )
        return redirect(reverse_node(self.kwargs.get('guid')))
