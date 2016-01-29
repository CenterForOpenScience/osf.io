from django.core.urlresolvers import reverse

from website.project.model import Node

from admin.abstract.views import GuidFormView
from .serializers import serialize_node
from .forms import NodeForm


class NodeFormView(GuidFormView):
    form_class = NodeForm
    template_name = 'nodes/node.html'
    object_type = 'node'

    def get_guid_object(self):
        return serialize_node(Node.load(self.guid))

    @property
    def success_url(self):
        return reverse('nodes:node') + '?guid={}'.format(self.guid)
