from rest_framework import serializers as ser

from api.base.exceptions import Conflict
from api.base.serializers import (
    EnumField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse
from osf.exceptions import CannotFinalizeArtifactError, NoPIDError
from osf.models import Outcome, OutcomeArtifact, Registration
from osf.utils.outcomes import ArtifactTypes


MODEL_TO_SERIALIZER_FIELD_MAPPINGS = {
    'artifact_type': 'resource_type',
    'identifier__value': 'pid',
}

class ResourceSerializer(JSONAPISerializer):

    non_anonymized_fields = frozenset([
        'id',
        'type',
        'date_created',
        'date_modified',
        'description',
        'registration',
        'links',
    ])

    class Meta:
        type_ = 'resources'

    id = ser.CharField(source='_id', read_only=True, required=False)
    type = TypeField()

    date_created = VersionedDateTimeField(source='created', required=False)
    date_modified = VersionedDateTimeField(source='modified', required=False)

    description = ser.CharField(allow_null=False, allow_blank=True, required=False)
    resource_type = EnumField(ArtifactTypes, source='artifact_type', allow_null=False, required=False)
    finalized = ser.BooleanField(required=False)

    # Reference to obj.identifier.value, populated via annotation on default manager
    pid = ser.CharField(allow_null=False, allow_blank=True, required=False)

    # primary_resource_guid is populated via annotation on the default manager
    registration = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<primary_resource_guid>'},
        read_only=True,
        required=False,
        allow_null=True,
    )

    links = LinksField({'self': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'resources:resource-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'resource_id': obj._id,
            },
        )

    def create(self, validated_data):
        # Already loaded by view, so no need to error check
        guid = self.context['request'].data['registration']
        primary_registration = Registration.load(guid)

        try:
            root_outcome = Outcome.objects.for_registration(primary_registration, create=True)
        except NoPIDError:
            raise Conflict('Cannot add Resources to a Registration that does not have a DOI')

        return OutcomeArtifact.objects.create(outcome=root_outcome)

    def update(self, instance, validated_data):
        updated_title = validated_data.get('title')
        if updated_title is not None:
            instance.title = updated_title

        updated_description = validated_data.get('description')
        if updated_description is not None:
            instance.description = updated_description

        updated_artifact_type = validated_data.get('artifact_type')
        if updated_artifact_type:  # Disallow resetting artifact_type to UNDEFINED
            instance.artifact_type = updated_artifact_type

        updated_pid = validated_data.get('pid')
        if updated_pid and updated_pid != instance.pid:  # Disallow resetting pid to ''
            instance.update_identifier(updated_pid, api_request=self.context['request'])

        finalized = validated_data.get('finalized')
        if finalized is not None:
            self._update_finalized(instance, finalized)

        instance.save()
        return instance

    def _update_finalized(self, instance, patched_finalized):
        # No change -> noop
        if instance.finalized == patched_finalized:
            return

        # Previous check alerts us that patched_finalized is False here
        if instance.finalized:
            raise Conflict(
                detail=(
                    'Resource with id [{instance._id}] has state `finalized: true`, '
                    'cannot PATCH `finalized: false'
                ),
                source={'pointer': '/data/attributes/finalized'},
            )

        try:
            instance.finalize(api_request=self.context['request'])
        except CannotFinalizeArtifactError as e:
            error_sources = [
                MODEL_TO_SERIALIZER_FIELD_MAPPINGS[field] for field in e.incomplete_fields
            ]
        else:
            return

        source = '/data/attributes/'
        if len(error_sources) == 1:  # Be more specific if possible
            source += error_sources[0]

        raise Conflict(
            detail=(
                f'Cannot PATCH `finalized: true` for Resource with id [{instance._id}] '
                f'until the following  required fields are populated {error_sources}.'
            ),
            source={'pointer': source},
        )

        return True
