from datetime import datetime
from django.shortcuts import redirect

from website.project.model import Node

from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_node
from .serializers import serialize_node


def remove_node(request, guid):
    node = Node.load(guid)
    node.is_deleted = True  # Auth required for
    node.deleted_date = datetime.utcnow()
    node.save()
    return redirect(reverse_node(guid))


def restore_node(request, guid):
    node = Node.load(guid)
    node.is_deleted = False
    node.deleted_date = None
    node.save()
    return redirect(reverse_node(guid))


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
