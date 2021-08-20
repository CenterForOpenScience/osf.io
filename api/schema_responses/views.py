from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import ParentWriteContributorOrPublic

from api.schema_responses.serializers import (
    SchemaResponsesListSerializer,
    SchemaResponsesDetailSerializer,
)
from osf.models import SchemaResponses
from api.base.filters import ListFilterMixin


class SchemaResponsesList(JSONAPIBaseView, ListFilterMixin, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponsesListSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-list'

    def get_queryset(self):
        return SchemaResponses.objects.filter()  # TODO: Filter for status


class SchemaResponsesDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ParentWriteContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponsesDetailSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_object(self):
        return SchemaResponses.objects.get(_id=self.kwargs['schema_response_id'])
