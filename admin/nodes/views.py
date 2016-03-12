from django.views.generic import ListView

from website.project.model import Node
from modularodm import Q

from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_node
from .serializers import serialize_node


class NodeFormView(GuidFormView):
    template_name = 'nodes/search.html'
    object_type = 'node'

    @property
    def success_url(self):
        return reverse_node(self.guid)


class NodeView(GuidView):
    template_name = 'nodes/node.html'
    context_object_name = 'node'

    def get_object(self, queryset=None):
        self.guid = self.kwargs.get('guid', None)
        return serialize_node(Node.load(self.guid))


class RegistrationListView(ListView):
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
