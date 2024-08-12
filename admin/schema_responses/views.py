from osf.models import SchemaResponse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, TemplateView


class SchemaResponseDetailView(PermissionRequiredMixin, TemplateView):
    """ """

    template_name = "schema_response/schema_response.html"
    permission_required = "osf.view_schema_response"
    raise_exception = True

    def get_object(self):
        schema_response = SchemaResponse.objects.get(
            id=self.kwargs["schema_response_id"]
        )

        # django admin templates don't like attributes with underscores for some reason
        schema_response.parent_guid = schema_response.parent._id
        return schema_response

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(
            *args, **{"schema_response": self.get_object()}, **kwargs
        )


class SchemaResponseListView(PermissionRequiredMixin, ListView):
    """ """

    template_name = "schema_response/schema_response_list.html"
    permission_required = "osf.view_schema_response"
    raise_exception = True

    def get_queryset(self):
        return SchemaResponse.objects.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        return {"schema_responses": self.get_queryset()}
