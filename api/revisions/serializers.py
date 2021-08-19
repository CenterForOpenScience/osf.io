from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, LinksField
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.serializers import (
    RelationshipField,
    VersionedDateTimeField,
)

from osf.models import (
    Registration,
    SchemaResponses,
    SchemaResponseBlock,
    RegistrationSchemaBlock,
)


class SchemaResponsesSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'date_created',
        'date_modified',
        'revision_justification',
        'reviews_state',
    ])

    id = ser.CharField(source='_id', required=False, allow_null=True)
    date_created = VersionedDateTimeField(source='created', required=False)
    date_modified = VersionedDateTimeField(source='modified', required=False)
    revision_justification = ser.CharField(required=False)
    revision_response = ser.JSONField(source='schema_responses', required=False)
    reviews_state = ser.ChoiceField(choices=['revision_in_progress', 'revision_pending_admin_approval', 'revision_pending_moderation', 'approved'], required=False)
    is_pending_current_user_approval = ser.SerializerMethodField()

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
        type_ = 'revisions'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'revisions:schema-responses-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'revision_id': obj._id,
            },
        )

    def get_is_pending_current_user_approval(self, obj):
        # TBD
        return False


class SchemaResponsesListSerializer(SchemaResponsesSerializer):

    def create(self, validated_data):
        registration = Registration.load(validated_data.pop('_id'))
        if registration.registered_schema.first():
            schema_response = SchemaResponses.objects.create(
                **validated_data,
                object_id=registration.id,
                content_type=ContentType.objects.get_for_model(registration),
                initiator=self.context['request'].user
            )
        else:
            raise NotImplementedError()

        return schema_response


class SchemaResponsesDetailSerializer(SchemaResponsesSerializer):

    writeable_method_fields = frozenset([
        'revision_response',
    ])
    revision_response = ser.SerializerMethodField()
    revised_responses = ser.SerializerMethodField()

    def get_revision_response(self, obj):
        data = []
        for response_block in obj.response_blocks.all():
            data.append({response_block.schema_key: response_block.response})
        return data

    def get_revised_responses(self, obj):
        previous_version = obj.previous_version

        if not previous_version:
            return []
        else:
            return obj.response_blocks.values_list('schema_key', flat=True)

    def update(self, revision, validated_data):
        schema_responses = validated_data.get('revision_response')
        schema = revision.parent.registered_schema.first()
        if not schema:
            raise exceptions.ValidationError('Schema Response parent must have a schema.')

        for key, response in schema_responses.items():
            try:
                block = RegistrationSchemaBlock.objects.get(
                    registration_response_key=key,
                    schema=schema,
                )
            except RegistrationSchemaBlock.DoesNotExist:
                raise exceptions.ValidationError(f'Schema Response key "{key}" not found in schema "{schema.name}"')

            # don't add exactly the same block if the current or previous version has it too.
            previous_version = revision.previous_version
            if revision.response_blocks.filter(schema_key=key, response=response):
                continue
            elif previous_version and previous_version.response_blocks.filter(schema_key=key, response=response):
                continue
            else:
                response_block, created = SchemaResponseBlock.objects.get_or_create(
                    schema_key=key,
                    source_block=block,
                )
                response_block.response = response
                response_block.save()
                revision.response_blocks.add(response_block)

        revision.save()

        return revision
