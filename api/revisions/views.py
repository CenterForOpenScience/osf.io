from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import ContributorOrPublic
from api.revisions.serializers import (
    SchemaResponsesListSerializer,
    SchemaResponsesDetailSerializer,
)
from osf.models import SchemaResponses, RegistrationAction
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON
from api.actions.serializers import RegistrationActionSerializer
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error
from osf.models import Registration

class SchemaResponsesList(JSONAPIBaseView, generics.ListCreateAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = SchemaResponsesListSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-list'

    def get_queryset(self):
        return SchemaResponses.objects.filter()  # TODO: Filter for status


class SchemaResponsesDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponsesDetailSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_object(self):
        return SchemaResponses.objects.get(_id=self.kwargs['revision_id'])


class SchemaResponsesActionList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = RegistrationActionSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-actions-list'
    node_lookup_url_kwarg = 'revision_id'

    def get_default_queryset(self):
        registration = SchemaResponses.objects.get(_id=self.kwargs['revision_id']).parent
        return registration.actions.all()

    def get_queryset(self):
        return self.get_queryset_from_request()


class SchemaResponsesActionDetail(JSONAPIBaseView,  ListFilterMixin, generics.ListCreateAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = RegistrationActionSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-actions-detail'

    def get_object(self):
        registration = SchemaResponses.objects.get(_id=self.kwargs['revision_id']).parent
        return registration.actions.get(_id=self.kwargs['action_id'])
