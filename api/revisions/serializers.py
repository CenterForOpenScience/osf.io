from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    VersionedDateTimeField,
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
    date_created = VersionedDateTimeField(source='created')
    date_modified = VersionedDateTimeField(source='modified')
    revision_justification = ser.CharField(source='justification')
    revision_response = ser.JSONField(source='all_responses')
    reviews_state = ser.ChoiceField(choices=['revision_in_progress', 'revision_pending_admin_approval', 'revision_pending_moderation', 'approved'], read_only=True)
    is_pending_current_user_approval = ser.SerializerMethodField()

    links = LinksField(
        {
            'self': 'get_absolute_url',
        },
    )

    registration = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent._id>'},
        read_only=True,
    )

    registration_schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<parent.registered_schema_id>'},
        read_only=True,
    )

    initiated_by = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<initiator._id>'},
        read_only=True,
    )

    class Meta:
        type_ = 'revisions'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'registrations:schema-responses-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'node_id': obj.parent._id,
                'revision_id': obj._id,
            },
        )

    def get_is_pending_current_user_approval(self, obj):
        # TBD
        return False


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

    def update(self, revision, validated_data):
        title = validated_data.get('title')
        public = validated_data.get('public')
        deleted = validated_data.get('deleted')
        responses = validated_data.get('responses')

        if deleted:
            revision.deleted = timezone.now()
            return revision
        if title:
            revision.title = title

        #report.set_public(public)

        try:
            revision.responses = responses
        except Exception as e:
            raise exceptions.ValidationError(e.message)

        revision.save()

        return revision