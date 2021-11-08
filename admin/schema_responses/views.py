from osf.models import SchemaResponse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView, ListView


class SchemaResponseDetailView(PermissionRequiredMixin, DetailView):
    """
    """
    template_name = 'schema_response/schema_response.html'
    permission_required = 'osf.view_schema_response'
    raise_exception = True

    def get_object(self, schema_response_id):
        return SchemaResponse.objects.get(id=schema_response_id)


class SchemaResponseListView(PermissionRequiredMixin, ListView):
    """
    """
    template_name = 'schema_response/schema_response_list.html'
    permission_required = 'osf.view_schema_response'
    raise_exception = True

    def get_queryset(self):
        return SchemaResponse.objects.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        return {'schema_responses': self.get_queryset()}
