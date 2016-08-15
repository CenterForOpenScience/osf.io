from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, RelationshipField
)
from api.base.utils import absolute_reverse


class PreprintProviderSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'name',
        'description',
        'id'
    ])

    name = ser.CharField(required=True)
    description = ser.CharField(required=False)
    id = ser.CharField(max_length=200, source='_id')

    # preprints = RelationshipField(
    #     related_view='preprints:preprint_list',
    #     related_view_kwargs={'preprint_id': '<_id>'}
    # )

    class Meta:
        type_ = 'preprint_providers'
