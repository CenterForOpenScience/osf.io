from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, RelationshipField

class InstitutionSerializer(JSONAPISerializer):
    name = ser.CharField(required=True)
    id = ser.CharField(required=True, source='_id')

    nodes = RelationshipField(
        related_view='institutions:institution-nodes',
        related_view_kwargs={'institution_id': '<pk>'},
    )

    users = RelationshipField(
        related_view='institutions:institution-users',
        related_view_kwargs={'institution_id': '<pk>'}
    )

    class Meta:
        type_ = 'institutions'

class InstitutionDetailSerializer(InstitutionSerializer):
    pass
