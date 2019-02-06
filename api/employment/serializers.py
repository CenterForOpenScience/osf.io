from rest_framework import serializers as ser
from api.base.utils import absolute_reverse
from api.base.serializers import BaseProfileSerializer, IDField
from osf.models import Employment


class EmploymentSerializer(BaseProfileSerializer):
    title = ser.CharField(required=False)

    class Meta:
        type_ = 'employment'

    def self_url(self, obj):
        return absolute_reverse(
            'employment:employment-detail', kwargs={
                'employment_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def create(self, validated_data):
        user = self.context['request'].user
        employment = Employment(user=user, **validated_data)
        employment.save()
        return employment

class EmploymentDetailSerializer(EmploymentSerializer):
    institution = ser.CharField(required=False)
    id = IDField(source='_id', required=True)

    def update(self, employment, validated_data):
        for attr, value in validated_data.items():
            setattr(employment, attr, value)
        employment.save()
        return employment
