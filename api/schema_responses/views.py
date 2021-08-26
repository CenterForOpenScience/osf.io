from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import SchemaResponseViewPermission

from api.schema_responses.serializers import (
    SchemaResponseRegistrationParentSerializer,
)
from osf.models import SchemaResponse, Registration
from api.base.filters import ListFilterMixin


class SchemaResponseList(JSONAPIBaseView, ListFilterMixin, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponseRegistrationParentSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-list'

    def get_queryset(self):
        return SchemaResponse.objects.filter()  # TODO: Filter for status


class SchemaResponseDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        SchemaResponseViewPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_serializer_class(self):
        parent = self.get_object().parent

        if isinstance(parent, Registration):
            return SchemaResponseRegistrationParentSerializer
        else:
            raise NotImplementedError()


    def get_object(self):
        return SchemaResponse.objects.get(_id=self.kwargs['schema_response_id'])

    def perform_destroy(self, instance):
        ## check state
        instance.delete()
