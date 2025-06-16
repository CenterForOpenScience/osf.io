from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers as ser
from api.nodes.serializers import RegistrationProviderRelationshipField
from api.collections_providers.fields import CollectionProviderRelationshipField
from api.preprints.serializers import PreprintProviderRelationshipField
from osf.models import Node
from website.util import api_v2_url


from api.base.serializers import JSONAPISerializer, LinksField
from .fields import FrequencyField

class SubscriptionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'event_name',
        'frequency',
    ])

    id = ser.CharField(read_only=True)
    event_name = ser.CharField(read_only=True)
    frequency = FrequencyField(source='*', required=True)

    class Meta:
        type_ = 'subscription'

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def update(self, instance, validated_data):
        user = self.context['request'].user
        frequency = validated_data.get('frequency')

        if frequency != 'none' and instance.content_type == ContentType.objects.get_for_model(Node):
            node = Node.objects.get(
                id=instance.id,
                content_type=instance.content_type,
            )
            user_subs = node.parent_node.child_node_subscriptions
            if node._id not in user_subs.setdefault(user._id, []):
                user_subs[user._id].append(node._id)
                node.parent_node.save()

        return instance


class RegistrationSubscriptionSerializer(SubscriptionSerializer):
    provider = RegistrationProviderRelationshipField(
        related_view='providers:registration-providers:registration-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False,
        required=False,
    )

    def get_absolute_url(self, obj):
        return api_v2_url(f'registration_subscriptions/{obj._id}')

    class Meta:
        type_ = 'registration-subscription'


class CollectionSubscriptionSerializer(SubscriptionSerializer):
    provider = CollectionProviderRelationshipField(
        related_view='providers:collection-providers:collection-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False,
        required=False,
    )

    def get_absolute_url(self, obj):
        return api_v2_url(f'collection_subscriptions/{obj._id}')

    class Meta:
        type_ = 'collection-subscription'


class PreprintSubscriptionSerializer(SubscriptionSerializer):
    provider = PreprintProviderRelationshipField(
        related_view='providers:preprint-providers:preprint-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False,
    )

    def get_absolute_url(self, obj):
        return api_v2_url(f'preprints_subscriptions/{obj._id}')

    class Meta:
        type_ = 'preprint-subscription'
