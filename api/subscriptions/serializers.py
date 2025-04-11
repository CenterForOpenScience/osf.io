from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField
from website.util import api_v2_url
from .fields import FrequencyField
from api.nodes.serializers import RegistrationProviderRelationshipField
from api.collections_providers.fields import CollectionProviderRelationshipField
from api.preprints.serializers import PreprintProviderRelationshipField


class SubscriptionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'event_name',
    ])

    id = ser.CharField(source='_id', read_only=True)
    event_name = ser.CharField(read_only=True)
    frequency = FrequencyField(source='*', required=True)
    links = LinksField({
        'self': 'get_absolute_url',
    })

    class Meta:
        type_ = 'subscription'

    def get_absolute_url(self, obj):
        return api_v2_url(f'subscriptions/{obj.pk}')

    def update(self, instance, validated_data):
        user = self.context['request'].user
        notification_type = validated_data.get('notification_type')
        instance.add_user_to_subscription(user, notification_type, save=True)
        return instance

class RegistrationSubscriptionSerializer(SubscriptionSerializer):
    provider = RegistrationProviderRelationshipField(
        related_view='providers:registration-providers:registration-provider-detail',
        related_view_kwargs={'provider_id': '<subscribed_object._id>'},
        read_only=False,
        required=False,
    )

    def get_absolute_url(self, obj):
        return api_v2_url(f'registration_subscriptions/{obj.pk}')

    class Meta:
        type_ = 'registration-subscription'

class CollectionSubscriptionSerializer(SubscriptionSerializer):
    provider = CollectionProviderRelationshipField(
        related_view='providers:collection-providers:collection-provider-detail',
        related_view_kwargs={'provider_id': '<subscribed_object._id>'},
        read_only=False,
        required=False,
    )

    def get_absolute_url(self, obj):
        return api_v2_url(f'collection_subscriptions/{obj.pk}')

    class Meta:
        type_ = 'collection-subscription'

class PreprintSubscriptionSerializer(SubscriptionSerializer):
    provider = PreprintProviderRelationshipField(
        related_view='providers:preprint-providers:preprint-provider-detail',
        related_view_kwargs={'provider_id': '<subscribed_object._id>'},
        read_only=False,
        required=False,
    )

    def get_absolute_url(self, obj):
        return api_v2_url(f'preprints_subscriptions/{obj.pk}')

    class Meta:
        type_ = 'preprint-subscription'
