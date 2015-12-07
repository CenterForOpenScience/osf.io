from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, RelationshipField, LinksField

class InstitutionSerializer(JSONAPISerializer):
    name = ser.CharField(required=True)
    id = ser.CharField(required=True, source='_id')

    links = LinksField({'self': 'get_api_url',
                        'html': 'get_absolute_url',})

    nodes = RelationshipField(
        related_view='institutions:institution-nodes',
        related_view_kwargs={'institution_id': '<pk>'},
    )

    users = RelationshipField(
        related_view='institutions:institution-users',
        related_view_kwargs={'institution_id': '<pk>'}
    )

    def get_api_url(self, obj):
        return obj.get_api_url()

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

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
