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
        return ''

class UserProviderSubscriptionSerializer(JSONAPISerializer):
    id = ser.CharField(source='_id', read_only=True)
    event_name = ser.CharField(read_only=True)
    frequency = FrequencyField(source='*')
    class Meta:
        type_ = 'user-provider-subscription'