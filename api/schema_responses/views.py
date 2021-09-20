from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.parsers import (
    JSONSchemaParser,
    JSONAPIParser,
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.nodes.permissions import (
    SchemaResponseDetailPermission,
    SchemaResponseListPermission,
    SchemaResponseActionPermission,
)
from api.schema_responses.serializers import (
    RegistrationSchemaResponseSerializer,
)
from api.actions.serializers import SchemaResponseActionSerializer
from osf.models import SchemaResponse, SchemaResponseAction, Registration
from api.base.filters import ListFilterMixin
from api.schema_responses.schemas import create_schema_response_payload
from framework.auth.oauth_scopes import CoreScopes
from api.base.utils import get_object_or_error


class SchemaResponseList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView):
    permission_classes = (
        SchemaResponseListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

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

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_serializer_class(self):
        parent = self.get_object().parent

        if isinstance(parent, Registration):
            return RegistrationSchemaResponseSerializer
        else:
            raise NotImplementedError()

    def get_object(self):
        return get_object_or_error(
            SchemaResponse,
            self.kwargs['schema_response_id'],
            request=self.request,
        )

    def perform_destroy(self, instance):
        ## check state
        instance.delete()


class SchemaResponseActionList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView):
    permission_classes = (
        SchemaResponseActionPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)

    view_category = 'schema_responses'
    view_name = 'schema-response-action-list'
    serializer_class = SchemaResponseActionSerializer

    def get_queryset(self):
        return SchemaResponseAction.objects.all()  # TODO: What to do here?


class SchemaResponseActionDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        SchemaResponseActionPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    serializer_class = SchemaResponseActionSerializer

    def get_object(self):
        return get_object_or_error(
            SchemaResponseAction,
            query_or_pk=self.kwargs['schema_response_action_id'],
            request=self.request,
        )
