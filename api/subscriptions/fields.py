from rest_framework import serializers as ser
from osf.models import NotificationSubscription

class FrequencyField(ser.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=['none', 'instantly', 'daily', 'weekly', 'monthly'], **kwargs)

    def to_representation(self, obj: NotificationSubscription):
        return obj.message_frequency

    def to_internal_value(self, freq):
        return super().to_internal_value(freq)
