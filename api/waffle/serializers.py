from waffle import flag_is_active, sample_is_active, switch_is_active
from waffle.models import Sample, Flag, Switch
from rest_framework import serializers as ser

from api.base.serializers import (JSONAPISerializer, TypeField)

class WaffleSerializer(JSONAPISerializer):
    id = ser.CharField(source='name', required=True, help_text='The id of the waffle object, which is the same as the name')
    type = TypeField()
    name = ser.CharField(required=True, help_text='The name of the waffle object')
    active = ser.SerializerMethodField()
    note = ser.CharField(required=False, allow_blank=True, help_text='Describe where the waffle object is used.')

    def get_active(self, obj):
        """
        Use waffle helper to determine if waffle object is active
        """
        return {
            Flag: self.lookup_flag,
            Sample: self.lookup_sample,
            Switch: self.lookup_switch
        }.get(type(obj))(obj)

    def lookup_flag(self, obj):
        return flag_is_active(self.context.get('request'), obj)

    def lookup_sample(self, obj):
        return sample_is_active(obj)

    def lookup_switch(self, obj):
        return switch_is_active(obj)

    class Meta:
        type_ = 'waffle',
