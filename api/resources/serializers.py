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
from osf.models import Outcome, OutcomeArtifact, Registration
from osf.utils.outcomes import ArtifactTypes, NoPIDError

class ResourceSerializer(JSONAPISerializer):

    non_anonymized_fields = frozenset([
        'id',
        'type',
        'date_created',
        'date_modified',
        'name',
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

    name = ser.CharField(allow_null=False, allow_blank=True, required=False)
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
            raise Conflict('Cannot add Resrouces to a Registration without a DOI')

        return OutcomeArtifact.objects.create(outcome=root_outcome)
