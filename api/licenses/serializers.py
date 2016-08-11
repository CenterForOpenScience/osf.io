from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, LinksField, IDField, TypeField
)
from api.base.utils import absolute_reverse


class LicenseSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'name',
        'id',
    ])
    non_anonymized_fields = ['type']
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(required=True, help_text='License name')
    text = ser.CharField(required=True, help_text='Full text of the license')
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'licenses'

    def get_absolute_url(self, obj):
        return absolute_reverse('licenses:license-detail', kwargs={'license_id': obj._id})
