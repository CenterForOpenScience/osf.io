from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)

from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from osf.models.schema_responses import SchemaResponses
from osf.models import Registration
from rest_framework import exceptions
from django.utils import timezone


class SchemaResponsesSerializer(JSONAPISerializer):
    id = ser.CharField(required=False, source='_id', read_only=True)
    responses = ser.JSONField(required=False)
    deleted = ser.SerializerMethodField(required=False)
    public = ser.SerializerMethodField(required=False)

    def get_deleted(self, obj):
        return bool(obj.deleted)

    def get_public(self, obj):
        return bool(obj.public)

    links = LinksField(
        {
            'self': 'get_absolute_url',
        },
    )

    registration = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<node._id>'},
        read_only=True,
    )

    registration_schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<schema._id>'},
        read_only=True,
    )

    class Meta:
        type_ = 'schema-responses'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'schema_responses:schema-responses-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'responses_id': obj._id,
            },
        )

class SchemaResponsesListSerializer(SchemaResponsesSerializer):
    def create(self, validated_data):

        try:
            # This must pull node_id from url args for NodeViews
            guid = self.initial_data.get('node') or self.context['view'].kwargs['node_id']
        except KeyError:
            raise exceptions.ValidationError('Request did not include node id')

        registration = Registration.load(guid)

        if registration.registered_schema.first():
            schema_response = SchemaResponses.objects.create(
                **validated_data,
                node=registration,
                registration_schema=registration.registered_schema.first()  # current only used as a one-to-one
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
        public = validated_data.get('public')
        deleted = validated_data.get('deleted')
        responses = validated_data.get('responses')

        if deleted:
            report.deleted = timezone.now()
            return report
        if title:
            report.title = title

        report.set_public(public)

        try:
            report.responses = responses
        except Exception as e:
            raise exceptions.ValidationError(e.message)

        report.save()

        return report
