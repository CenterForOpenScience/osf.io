from rest_framework import serializers as ser

from website.models import Institution
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

    def create(self, validated_data):
        node = self.context['view'].get_node()
        inst = validated_data['_id']
        user = self.context['request'].user
        if inst == 'None':
            node.remove_primary_institution()
        else:
            institution = Institution.load(inst)
            if institution:
                node.add_primary_institution(user=user, inst=institution)
        return institution

    class Meta:
        type_ = 'institutions'

class InstitutionDetailSerializer(InstitutionSerializer):
    pass
