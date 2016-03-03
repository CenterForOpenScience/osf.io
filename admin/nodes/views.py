from django.shortcuts import redirect

from website.project.model import Node, User

from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_node
from .serializers import serialize_node


def remove_contributor(request, node_id, user_id):
    user = User.load(user_id)
    node = Node.load(node_id)
    node.remove_contributor(user, None, log=False)  # TODO: log on OSF as admin
    return redirect(reverse_node(node_id))


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
