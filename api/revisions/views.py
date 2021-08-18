from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import ContributorOrPublic
from api.revisions.serializers import (
    SchemaResponsesListSerializer,
    SchemaResponsesDetailSerializer,
)
from osf.models import SchemaResponses

class SchemaResponsesList(JSONAPIBaseView, generics.ListCreateAPIView):
    permission_classes = (
        ContributorOrPublic,
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
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponsesDetailSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_object(self):
        return SchemaResponses.objects.get(_id=self.kwargs['revision_id'])
