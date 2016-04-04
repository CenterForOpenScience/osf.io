from __future__ import unicode_literals

from django.views.generic import ListView, DeleteView
from datetime import datetime
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from modularodm import Q

from website.models import Node, User
from admin.base.views import GuidFormView, GuidView
from admin.base.utils import OSFAdmin
from admin.nodes.templatetags.node_extras import reverse_node
from admin.nodes.serializers import serialize_node


class NodeFormView(OSFAdmin, GuidFormView):
    template_name = 'nodes/search.html'
    object_type = 'node'

    @property
    def success_url(self):
        return reverse_node(self.guid)


class NodeRemoveContributorView(OSFAdmin, DeleteView):
    template_name = 'nodes/remove_contributor.html'
    context_object_name = 'node'

    def delete(self, request, *args, **kwargs):
        try:
            node, user = self.get_object()
            node.remove_contributor(user, None, log=False)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('spam_id')
                    )
                )
            )
        return redirect(reverse_node(self.kwargs.get('guid')))

    def get_object(self, queryset=None):
        return (Node.load(self.kwargs.get('node_id')),
                User.load(self.kwargs.get('user_id')))


class NodeDeleteView(OSFAdmin, DeleteView):
    template_name = 'nodes/remove_node.html'
    context_object_name = 'node'

    def delete(self, request, *args, **kwargs):
        try:
            node = self.get_object()
            if node.is_deleted:
                node.is_deleted = False
                node.deleted_date = None
            elif not node.is_registration:
                node.is_deleted = True
                node.deleted_date = datetime.utcnow()
            node.save()
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('spam_id')
                    )
                )
            )
        return redirect(reverse_node(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(NodeDeleteView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return Node.load(self.kwargs.get('guid'))


class NodeView(OSFAdmin, GuidView):
    template_name = 'nodes/node.html'
    context_object_name = 'node'

    def get_object(self, queryset=None):
        return serialize_node(Node.load(self.kwargs.get('guid')))


class RegistrationListView(OSFAdmin, ListView):
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
