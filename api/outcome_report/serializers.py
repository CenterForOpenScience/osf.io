from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)

from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from osf.models import SchemaResponses

class SchemaResponsesSerializer(JSONAPISerializer):
    id = ser.CharField(source="_id", read_only=True)

    title = ser.CharField(required=False, allow_blank=True)
    description = ser.CharField(required=False, allow_blank=True)
    outcome_data = ser.JSONField(required=False)

    links = LinksField(
        {
            "self": "get_absolute_url",
        }
    )

    registration = RelationshipField(
        related_view="registrations:registration-detail",
        related_view_kwargs={"node_id": "<registration._id>"},
    )

    schema = RelationshipField(
        related_view="schemas:registration-schema-detail",
        related_view_kwargs={"schema_id": "<schema._id>"},
    )

    class Meta:
        type_ = "schema-responses"

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "schema-responses:schema-responses-detail",
            kwargs={
                "version": self.context["request"].parser_context["kwargs"]["version"],
                "schema_responses_id": obj._id,
            },
        )


class SchemaResponsesListSerializer(SchemaResponsesSerializer):
    def create(self, validated_data):
        outcome_report = SchemaResponses(
            **validated_data
        )
        outcome_report.save()

class SchemaResponsesDetailSerializer(SchemaResponsesSerializer):
    def update(self, report, validated_data):
        outcome_data = validated_data.get('outcome_data')

        report.outcome_data = outcome_data
