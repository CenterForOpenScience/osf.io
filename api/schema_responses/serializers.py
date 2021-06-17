from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)

from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from osf.models.schema_responses import SchemaResponses
from osf.models import Registration


class SchemaResponsesSerializer(JSONAPISerializer):
    id = ser.CharField(required=False, source='_id', read_only=True)
    title = ser.CharField(required=False, allow_blank=True)
    responses = ser.JSONField(required=False, source='_responses')
    deleted = ser.BooleanField(required=False)
    public = ser.BooleanField(required=False)

    links = LinksField(
        {
            'self': 'get_absolute_url',
        }
    )

    node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'},
        read_only=True,
    )

    schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<schema._id>'},
        read_only=True,
    )

    class Meta:
        type_ = 'schema_responses'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'schema_responses:schema-responses-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version"],
                'responses_id': obj._id,
            },
        )


class SchemaResponsesListSerializer(SchemaResponsesSerializer):
    def create(self, validated_data):
        node = Registration.load(self.initial_data['node'])

        if node.registered_schema.first():
            schema_response = SchemaResponses.objects.create(
                **validated_data,
                node=node,
                schema=node.registered_schema.first() # current only used as a one-to-one
            )
        else:
            raise NotImplementedError()

        return schema_response


class SchemaResponsesDetailSerializer(SchemaResponsesSerializer):

    versions = RelationshipField(
        related_view='registrations:schema-responses-list',
        related_view_kwargs={'node_id': '<node._id>'},
    )

    def update(self, report, validated_data):
        title = validated_data.get('title')
        responses = validated_data.get('responses')

        try:
            report.responses = responses
        except Exception:
            raise Exception('validation errors')

        report.title = title
        report.save()
