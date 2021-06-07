from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import ContributorOrPublic
from api.outcome_reports.serializers import (
    OutcomeReportListSerializer,
    OutcomeReportDetailSerializer,
)
from osf.models.outcome_report import OutcomeReport
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON


class OutcomeReportList(JSONAPIBaseView, generics.ListCreateAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = OutcomeReportListSerializer
    view_category = "outcome-reports"
    view_name = "outcome-reports-list"

    def get_queryset(self):
        return OutcomeReport.objects.filter(
            deleted__isnull=True,
            public__isnull=False
        )


class OutcomeReportDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = OutcomeReportDetailSerializer
    view_category = "outcome-reports"
    view_name = "outcome-reports-detail"

    def get_object(self):
        return OutcomeReport.objects.get(guids___id=self.kwargs["report_id"])


class OutcomeReportVersions(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = OutcomeReportDetailSerializer
    view_category = "outcome_reports"
    view_name = "outcome-reports-versions"

    ordering = ('-public',)

    def get_queryset(self):
        outcome_report = OutcomeReport.objects.get(guids___id=self.kwargs["report_id"])
        return OutcomeReport.objects.filter(
            deleted__isnull=True,
            public__isnull=False,
            node=outcome_report.node,
            schema=outcome_report.schema
        )

