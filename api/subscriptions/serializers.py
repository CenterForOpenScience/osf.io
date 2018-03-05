from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from api.base.serializers import JSONAPISerializer

NOTIFICATION_TYPES = {
    'none': 'none',
    'instant': 'email_transactional',
    'daily': 'email_digest'
}


class FrequencyField(ser.Field):
    def to_representation(self, obj):
        user = self.context['request'].user
        if user in obj.none.all():
            frequency = 'none'
        elif user in obj.email_transactional.all():
            frequency = 'instant'
        elif user in obj.email_digest.all():
            frequency = 'daily'
        return frequency

    def to_internal_value(self, data):
        if data not in NOTIFICATION_TYPES.keys():
            raise ValidationError('Invalid frequency "{}"'.format(data))
        return {'notification_type': NOTIFICATION_TYPES[data]}


class UserProviderSubscriptionListSerializer(JSONAPISerializer):
    id = ser.CharField(source='_id', read_only=True)
    event_name = ser.CharField(read_only=True)
    frequency = FrequencyField(source='*')

    class Meta:
        type_ = 'user-subscription'


class UserProviderSubscriptionDetailSerializer(JSONAPISerializer):
    id = ser.CharField(source='_id', read_only=True)
    event_name = ser.CharField(read_only=True)
    frequency = FrequencyField(source='*',required=True)

    class Meta:
        type_ = 'user-subscription'

    def update(self, instance, validated_data):
        user = self.context['request'].user
        notification_type = validated_data.get('notification_type')
        instance.add_user_to_subscription(user, notification_type, save=True)
        return instance
