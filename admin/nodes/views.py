from django.views.generic import FormView

from .forms import NodeForm


class NodeFormView(FormView):
    form_class = NodeForm
    template_name = 'nodes/node.html'

    def post(self, request, *args, **kwargs):
        return super(NodeFormView, self).post(request, *args, **kwargs)
