from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, LinksField
from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.serializers import (
    RelationshipField,
    VersionedDateTimeField,
)

from osf.models import (
    Registration,
    SchemaResponses,
    RegistrationSchema,
)


class SchemaResponsesSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'date_created',
        'date_modified',
        'revision_justification',
        'reviews_state',
    ])
    writeable_method_fields = frozenset([
        'revision_response',
    ])

    id = ser.CharField(source='_id', required=False, allow_null=True)
    date_created = VersionedDateTimeField(source='created', required=False)
    date_modified = VersionedDateTimeField(source='modified', required=False)
    revision_justification = ser.CharField(required=False)
    revised_responses = ser.JSONField(required=False)
    reviews_state = ser.ChoiceField(choices=['revision_in_progress', 'revision_pending_admin_approval', 'revision_pending_moderation', 'approved'], required=False)
    is_pending_current_user_approval = ser.SerializerMethodField()
    revision_response = ser.SerializerMethodField()

    def get_revision_response(self, obj):
        data = []
        for response_block in obj.response_blocks.all():
            data.append({response_block.schema_key: response_block.response})
        return data

    links = LinksField(
        {
            'self': 'get_absolute_url',
        },
    )

    registration = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent._id>'},
        required=False,
    )

    registration_schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<parent.registered_schema_id>'},
        read_only=True,
        required=False,
    )

    initiated_by = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<initiator._id>'},
        read_only=True,
        required=False,

    )

    class Meta:
        type_ = 'schema-responses'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'schema_responses:schema-responses-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'schema_response_id': obj._id,
            },
        )

    def get_is_pending_current_user_approval(self, obj):
        # TBD
        return False


class SchemaResponsesListSerializer(SchemaResponsesSerializer):

    def create(self, validated_data):
        registration = Registration.load(validated_data.pop('_id'))

        try:
            schema = registration.registered_schema.get()
        except RegistrationSchema.DoesNotExist:
            raise exceptions.ValidationError(f'Resource {registration._id} must have schema')

        initiator = self.context['request'].user
        justification = validated_data.pop('revision_justification', '')

        schema_response = SchemaResponses.create_initial_responses(
            initiator=initiator,
            parent=registration,
            schema=schema,
            justification=justification,
        )

        return schema_response


class SchemaResponsesDetailSerializer(SchemaResponsesSerializer):

    def update(self, schema_response, validated_data):
        schema_responses = validated_data.get('revision_response')

        try:
            schema_response.update_responses(schema_responses)
        except ValueError as exc:
            raise exceptions.ValidationError(detail=str(exc))

        return schema_response
