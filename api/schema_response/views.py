from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import ContributorOrPublic
from api.schema_response.serializers import (
    SchemaResponseListSerializer,
    SchemaResponseDetailSerializer,
)
from osf.models.schema_responses import SchemaResponses
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON


class SchemaResponsesList(JSONAPIBaseView, generics.ListCreateAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = SchemaResponseListSerializer
    view_category = "schema-responses"
    view_name = "schema-responses-list"

    def get_queryset(self):
        return SchemaResponses.objects.filter(
            deleted__isnull=True,
            public__isnull=False
        )


class SchemaResponsesDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponseDetailSerializer
    view_category = "schema-responses"
    view_name = "schema-responses-detail"

    def get_object(self):
        return SchemaResponses.objects.get(guids___id=self.kwargs["report_id"])


class SchemaResponsesVersions(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponseDetailSerializer
    view_category = "schema-responses"
    view_name = "schema-responses-versions"

    ordering = ('-public',)

    def get_queryset(self):
        schema_response = SchemaResponses.objects.get(guids___id=self.kwargs["report_id"])
        return SchemaResponses.objects.filter(
            deleted__isnull=True,
            public__isnull=False,
            node=schema_response.node,
            schema=schema_response.schema
        )

