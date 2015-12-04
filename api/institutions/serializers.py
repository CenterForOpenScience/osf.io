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

    def update(self, instance, validated_data):
        node = self.context['view'].get_node()
        user = self.context['request'].user
        node.add_primary_institution(user=user, inst=instance)
        return instance

    def destroy(self, instance, validated_data):
        node = self.context['view'].get_node()
        node.remove_primary_institution()
        return instance

    class Meta:
        type_ = 'institutions'

class InstitutionDetailSerializer(InstitutionSerializer):
    pass
