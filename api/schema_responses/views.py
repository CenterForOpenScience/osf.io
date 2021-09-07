from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.parsers import JSONSchemaParser, JSONAPIParser
from api.nodes.permissions import SchemaResponseDetailPermission, SchemaResponseListPermission

from api.schema_responses.serializers import (
    RegistrationSchemaResponseSerializer,
)
from osf.models import SchemaResponse, Registration
from api.base.filters import ListFilterMixin
from api.schema_responses.schemas import create_schema_response_payload

class SchemaResponseList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView):
    permission_classes = (
        SchemaResponseListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIParser, JSONSchemaParser)

    serializer_class = RegistrationSchemaResponseSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-list'
    create_payload_schema = create_schema_response_payload

    def get_queryset(self):
        return SchemaResponse.objects.all()

    def get_parser_context(self, http_request):
        """
        Tells parser what json schema we are checking againest.
        """
        res = super().get_parser_context(http_request)
        res['json_schema'] = self.create_payload_schema
        return res


class SchemaResponseDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        SchemaResponseDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_serializer_class(self):
        parent = self.get_object().parent

        if isinstance(parent, Registration):
            return RegistrationSchemaResponseSerializer
        else:
            raise NotImplementedError()

    def get_object(self):
        return SchemaResponse.objects.get(_id=self.kwargs['schema_response_id'])

    def perform_destroy(self, instance):
        ## check state
        instance.delete()
