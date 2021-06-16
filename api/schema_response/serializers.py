from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)

from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from osf.models.schema_responses import SchemaResponses


class SchemaResponseSerializer(JSONAPISerializer):
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
        related_view="schema_response:schema-responses-versions",
        related_view_kwargs={"report_id": "<_id>"},
    )

    class Meta:
        type_ = "schema_response"

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "schema_response:schema-responses-detail",
            kwargs={
                "version": self.context["request"].parser_context["kwargs"]["version"],
                "report_id": obj._id,
            },
        )


class SchemaResponseListSerializer(SchemaResponseSerializer):
    def create(self, validated_data):
        title = validated_data.get('title')
        node = validated_data.get('node')
        responses = validated_data.get('responses')
        schema = validated_data.get('schema')

        SchemaResponses.objects.create(
            node_id=node.id,
            title=title,
            _responses=responses,
            schema=schema
        )


class SchemaResponseDetailSerializer(SchemaResponseSerializer):
    def update(self, report, validated_data):
        title = validated_data.get('title')
        responses = validated_data.get('responses')

        try:
            report.responses = responses
        except Exception:
            raise Exception('validation errors')

        report.title = title
        report.save()
