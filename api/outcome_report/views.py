from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from osf.models import SchemaResponses
from api.nodes.permissions import ContributorOrPublic
from api.outcome_report.serializers import (
    SchemaResponsesDetailSerializer,
    SchemaResponsesListSerializer,
)


class OutcomeReportList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponsesListSerializer
    view_category = "schema-responses"
    view_name = "schema-responses-list"

    def get_queryset(self):
        return SchemaResponses.objects.filter(deleted__isnull=True)


class OutcomeReportDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = SchemaResponsesDetailSerializer
    view_category = "schema-responses"
    view_name = "schema-responses-detail"

    def get_object(self):
        return SchemaResponses.objects.get(_id=self.kwargs["report_id"])
