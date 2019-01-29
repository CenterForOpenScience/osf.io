from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from api.base.serializers import BaseProfileSerializer


class EducationSerializer(BaseProfileSerializer):
    degree = ser.CharField(required=False)

    class Meta:
        type_ = 'education'

    def self_url(self, obj):
        return absolute_reverse(
            'education:education-detail', kwargs={
                'education_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )
