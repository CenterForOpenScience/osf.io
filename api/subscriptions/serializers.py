from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError
from api.nodes.serializers import RegistrationProviderRelationshipField
from api.collections_providers.fields import CollectionProviderRelationshipField
from api.preprints.serializers import PreprintProviderRelationshipField
from website.util import api_v2_url


from api.base.serializers import JSONAPISerializer, LinksField

NOTIFICATION_TYPES = {
    'none': 'none',
    'instant': 'email_transactional',
    'daily': 'email_digest',
}


class FrequencyField(ser.Field):
    def to_representation(self, obj):
        user_id = self.context['request'].user.id
        if obj.email_transactional.filter(id=user_id).exists():
            return 'instant'
        if obj.email_digest.filter(id=user_id).exists():
            return 'daily'
        return 'none'

    def to_internal_value(self, frequency):
        notification_type = NOTIFICATION_TYPES.get(frequency)
        if notification_type:
            return {'notification_type': notification_type}
        raise ValidationError(f'Invalid frequency "{frequency}"')

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
        return obj.absolute_api_v2_url

    def update(self, instance, validated_data):
        user = self.context['request'].user
        notification_type = validated_data.get('notification_type')
        instance.add_user_to_subscription(user, notification_type, save=True)
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
