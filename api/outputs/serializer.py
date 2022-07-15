from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse


class OutputSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'outputs'

    id = ser.CharField(source='_id', required=True, allow_null=False, read_only=True)
    type = TypeField()

    date_created = VersionedDateTimeField(source='created', required=False)
    date_modified = VersionedDateTimeField(source='modified', required=False)

    name = ser.CharField(allow_null=False, allow_blank=True, required=False)
    description = ser.CharField(allow_null=False, allow_blank=True, required=False)
    artifact_type = ser.IntegerField(allow_null=False, required=False)
    finalized = ser.BooleanField(allow_null=False, required=False)

    # Reference to obj.identifier.value, populated via annotation on default manager
    pid = ser.CharField(allow_null=False, allow_blank=True, required=False)

    registration = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': 'get_primary_registration_id'},
        read_only=True,
        required=False,
        allow_null=True,
    )

    links = LinksField({'self': 'get_absolute_url'})

    def get_primary_registration_id(self, obj):
        return obj.outcome.primary_osf_resource._id

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'outputs:output-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'output_id': obj._id,
            },
        )
