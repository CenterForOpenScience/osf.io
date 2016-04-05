from __future__ import unicode_literals

from django.views.generic import ListView, DeleteView
from datetime import datetime
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from modularodm import Q

from website.models import Node, User, NodeLog
from admin.base.views import GuidFormView, GuidView
from admin.base.utils import OSFAdmin
from admin.common_auth.logs import (
    update_admin_log,
    NODE_REMOVED,
    NODE_RESTORED,
    CONTRIBUTOR_REMOVED
)
from admin.nodes.templatetags.node_extras import reverse_node
from admin.nodes.serializers import serialize_node, serialize_simple_user


class NodeFormView(OSFAdmin, GuidFormView):
    """ Allow authorized admin user to input specific node guid.

    Basic form. No admin models.
    """
    template_name = 'nodes/search.html'
    object_type = 'node'

    @property
    def success_url(self):
        return reverse_node(self.guid)


class NodeRemoveContributorView(OSFAdmin, DeleteView):
    """ Allow authorized admin user to remove project contributor

    Interface with OSF database. No admin models.
    """
    template_name = 'nodes/remove_contributor.html'
    context_object_name = 'node'

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
                    date=datetime.utcnow(),
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
        context.setdefault('node_id', node.pk)
        context.setdefault('user', serialize_simple_user((user.pk, None)))
        return super(NodeRemoveContributorView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return (Node.load(self.kwargs.get('node_id')),
                User.load(self.kwargs.get('user_id')))


class NodeDeleteView(OSFAdmin, DeleteView):
    """ Allow authorized admin user to remove/hide nodes

    Interface with OSF database. No admin models.
    """
    template_name = 'nodes/remove_node.html'
    context_object_name = 'node'
    object = None

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
                node.deleted_date = datetime.utcnow()
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
                    date=datetime.utcnow(),
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
        return redirect(reverse_node(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object').pk)
        return super(NodeDeleteView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return Node.load(self.kwargs.get('guid'))


class NodeView(OSFAdmin, GuidView):
    """ Allow authorized admin user to view nodes

    View of OSF database. No admin models.
    """
    template_name = 'nodes/node.html'
    context_object_name = 'node'

    def get_object(self, queryset=None):
        return serialize_node(Node.load(self.kwargs.get('guid')))


class RegistrationListView(OSFAdmin, ListView):
    """ Allow authorized admin user to view list of registrations

    View of OSF database. No admin models.
    """
    template_name = 'nodes/registration_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date_created'
    context_object_name = '-node'

    def get_queryset(self):
        query = (
            Q('is_registration', 'eq', True)
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
