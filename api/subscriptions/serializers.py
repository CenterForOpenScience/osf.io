from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from api.base.serializers import (JSONAPISerializer, IDField)
from osf.models import OSFUser

from osf.models import PreprintProvider

frequencies = ['none', 'instant', 'daily']

class FrequencyField(ser.Field):
    def to_representation(self, obj):
        user_id = self.context['view'].kwargs['user_id']
        user = OSFUser.load(user_id)
        if user in obj.none.all():
            frequency = 'none'
        elif user in obj.email_transactional.all():
            frequency = 'instant'
        elif user in obj.email_digest.all():
            frequency = 'daily'
        return frequency

    def to_internal_value(self, data):
        if data not in frequencies:
            raise ValidationError('Invalid frequency "{}"'.format(data))
        return {'frequency': data}

class UserProviderSubscriptionSerializer(JSONAPISerializer):
    id = ser.CharField(source='_id', read_only=True)
    event_name = ser.CharField(read_only=True)
    frequency = FrequencyField(source='*')

    class Meta:
        type_ = 'user-provider-subscription'

    def update(self, instance, validated_data):
        user = OSFUser.load(self.context['view'].kwargs['user_id'])
        frequency = validated_data.get('frequency')
        if frequency:
            if frequency == 'none' and user not in instance.none.all():
                instance.email_digest.remove(user)
                instance.email_transactional.remove(user)
                instance.none.add(user)
                instance.save()
            elif frequency == 'daily' and user not in instance.email_digest.all():
                instance.none.remove(user)
                instance.email_transactional.remove(user)
                instance.email_digest.add(user)
                instance.save()
            elif frequency == 'instant' and user not in instance.email_transactional.all():
                instance.email_digest.remove(user)
                instance.none.remove(user)
                instance.email_transactional.add(user)
                instance.save()
        return instance