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

    id = ser.CharField(source='_id', read_only=True, required=False)
    type = TypeField()

    date_created = VersionedDateTimeField(source='created', required=False)
    date_modified = VersionedDateTimeField(source='modified', required=False)

    name = ser.CharField(allow_null=False, allow_blank=True, required=False)
    description = ser.CharField(allow_null=False, allow_blank=True, required=False)
    output_type = ser.IntegerField(source='artifact_type', allow_null=False, required=False)
    finalized = ser.BooleanField(required=False)

    # Reference to obj.identifier.value, populated via annotation on default manager
    pid = ser.CharField(allow_null=False, allow_blank=True, required=False)

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
            'outputs:output-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'output_id': obj._id,
            },
        )
