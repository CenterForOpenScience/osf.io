from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)

from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from osf.models.outcome_report import OutcomeReport


class OutcomeReportSerializer(JSONAPISerializer):
    id = ser.CharField(source="_id", read_only=True, required=False)
    title = ser.CharField(required=False, allow_blank=True)
    responses = ser.JSONField(source='_responses', required=False)
    deleted = ser.BooleanField(default=False, required=False)
    public = ser.BooleanField(default=False, required=False)

    links = LinksField(
        {
            "self": "get_absolute_url",
        }
    )

    node = RelationshipField(
        related_view="nodes:node-detail",
        related_view_kwargs={"node_id": "<node._id>"},
        read_only=False,
        required=True
    )

    schema = RelationshipField(
        related_view="schemas:registration-schema-detail",
        related_view_kwargs={"schema_id": "<schema._id>"},
    )

    versions = RelationshipField(
        related_view="outcome_reports:outcome-reports-versions",
        related_view_kwargs={"report_id": "<_id>"},
    )

    class Meta:
        type_ = "outcome_report"

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "outcome_reports:outcome-reports-detail",
            kwargs={
                "version": self.context["request"].parser_context["kwargs"]["version"],
                "report_id": obj._id,
            },
        )


class OutcomeReportListSerializer(OutcomeReportSerializer):
    def create(self, validated_data):
        title = validated_data.get('title')
        node = validated_data.get('node')
        responses = validated_data.get('responses')
        schema = validated_data.get('schema')

        OutcomeReport.objects.create(
            node_id=node.id,
            title=title,
            _responses=responses,
            schema=schema
        )


class OutcomeReportDetailSerializer(OutcomeReportSerializer):
    def update(self, report, validated_data):
        title = validated_data.get('title')
        responses = validated_data.get('responses')

        try:
            report.responses = responses
        except Exception:
            raise Exception('validation errors')

        report.title = title
        report.save()
