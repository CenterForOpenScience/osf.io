from rest_framework import generics, permissions as drf_permissions
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from osf.models import OutcomeReport
from api.nodes.permissions import ContributorOrPublic
from api.outcome_report.serializers import (
    OutcomeReportListSerializer,
    OutcomeReportDetailSerializer,
)


class OutcomeReportList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = OutcomeReportListSerializer
    view_category = "outcome-reports"
    view_name = "outcome-report-list"

    def get_queryset(self):
        return OutcomeReport.objects.filter(deleted__isnull=True)


class OutcomeReportDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = OutcomeReportDetailSerializer
    view_category = "outcome-reports"
    view_name = "outcome-report-detail"

    def get_object(self):
        return OutcomeReport.objects.get(_id=self.kwargs["report_id"])
