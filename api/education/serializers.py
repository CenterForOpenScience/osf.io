from rest_framework import serializers as ser

from api.base.utils import absolute_reverse
from api.base.serializers import BaseProfileSerializer, IDField
from osf.models import Education


class EducationSerializer(BaseProfileSerializer):
    degree = ser.CharField(required=False)
    schema = 'education-schema.json'

    class Meta:
        type_ = 'education'

    def self_url(self, obj):
        return absolute_reverse(
            'users:user-education-detail', kwargs={
                'education_id': obj._id,
                'user_id': obj.user._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def create(self, validated_data):
        user = self.context['request'].user
        education = Education(user=user, **validated_data)
        education.save()
        return education


class EducationDetailSerializer(EducationSerializer):
    institution = ser.CharField(required=False)
    id = IDField(source='_id', required=True)

    def update(self, education, validated_data):
        for attr, value in validated_data.items():
            setattr(education, attr, value)
        education.save()
        return education
