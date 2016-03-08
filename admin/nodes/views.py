from website.project.model import Node

from admin.base.views import GuidFormView
from admin.nodes.templatetags.node_extras import reverse_node
from .serializers import serialize_node


class NodeFormView(GuidFormView):
    template_name = 'nodes/node.html'
    object_type = 'node'

    def get_guid_object(self):
        return serialize_node(Node.load(self.guid))

    @property
    def success_url(self):
        return reverse_node(self.guid)
