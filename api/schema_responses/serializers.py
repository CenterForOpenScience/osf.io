from api.base.utils import absolute_reverse, get_object_or_error
from api.base.serializers import JSONAPISerializer, LinksField, TypeField
from api.base.exceptions import Conflict
from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.serializers import (
    RelationshipField,
    VersionedDateTimeField,
)

from osf.models import (
    Registration,
    SchemaResponse,
    RegistrationSchema,
)

from osf.utils.workflows import ApprovalStates


class RegistrationSchemaResponseSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'date_created',
        'date_modified',
        'revision_justification',
        'reviews_state',
    ])
    writeable_method_fields = frozenset([
        'revision_responses',
    ])

    id = ser.CharField(source='_id', required=True, allow_null=True)
    type = TypeField()
    date_created = VersionedDateTimeField(source='created', required=False)
    date_submitted = VersionedDateTimeField(source='submitted_timestamp', required=False)
    date_modified = VersionedDateTimeField(source='modified', required=False)
    revision_justification = ser.CharField(required=False)
    updated_response_keys = ser.JSONField(required=False, read_only=True)
    reviews_state = ser.ChoiceField(choices=ApprovalStates.char_field_choices(), required=False)
    revision_responses = ser.JSONField(source='all_responses', required=False)

    links = LinksField(
        {
            'self': 'get_absolute_url',
        },
    )

    registration = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent._id>'},
        read_only=True,
        required=False,
    )

    registration_schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<schema._id>'},
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
        type_ = 'revisions'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'schema_responses:schema-responses-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'schema_response_id': obj._id,
            },
        )

    def create(self, validated_data):
        try:
            registration_id = validated_data.pop('_id')
        except KeyError:
            raise exceptions.ValidationError('payload must contain valid Registration id')

        registration = get_object_or_error(
            Registration,
            query_or_pk=registration_id,
            request=self.context['request'],
        )

        try:
            schema = registration.registration_schema
        except RegistrationSchema.DoesNotExist:
            raise exceptions.ValidationError(f'Resource {registration._id} must have schema')

        initiator = self.context['request'].user
        justification = validated_data.pop('revision_justification', '')

        if not registration.schema_responses.exists():
            schema_response = SchemaResponse.create_initial_response(
                initiator=initiator,
                parent=registration,
                schema=schema,
                justification=justification,
            )
        else:
            schema_response = SchemaResponse.create_from_previous_response(
                initiator=initiator,
                previous_response=registration.schema_responses.order_by('-created').first(),
                justification=justification,
            )

        return schema_response

    def update(self, schema_response, validated_data):
        if schema_response.reviews_state != ApprovalStates.IN_PROGRESS.db_name:
            raise Conflict(
                detail=f'Schema Response is in `{schema_response.reviews_state}` state must be'
                       f' {ApprovalStates.IN_PROGRESS.db_name}',
            )

        revision_responses = validated_data.get('revision_responses')
        justification = validated_data.get('revision_justification')

        if justification:
            schema_response.revision_justification = justification

        if revision_responses:
            try:
                schema_response.update_responses(revision_responses)
            except ValueError as exc:
                raise exceptions.ValidationError(detail=str(exc))

        schema_response.save()
        return schema_response
