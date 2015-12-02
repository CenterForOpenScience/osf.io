from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer

class InstitutionSerializer(JSONAPISerializer):
    name = ser.CharField(required=True)
    id = ser.CharField(required=True, source='_id')

    class Meta:
        type_ = 'institutions'

class InstitutionDetailSerializer(InstitutionSerializer):
    pass
