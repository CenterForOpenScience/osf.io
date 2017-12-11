from waffle import flag_is_active, sample_is_active, switch_is_active
from waffle.models import Sample, Flag, Switch
from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, TypeField, IDField
from api.base.waffle_decorators import waffle_feature_is_active

class WaffleSerializer(JSONAPISerializer):
    id = ser.SerializerMethodField()
    type = TypeField()
    name = ser.CharField(required=True, help_text='The name of the waffle object')
    active = ser.SerializerMethodField()
    note = ser.CharField(required=False, allow_blank=True, help_text='Describe where the waffle object is used.')

    def get_active(self, obj):
        """
        Use waffle_feature_is_active helper to determine if waffle flag, sample, or switch is active
        """
        return waffle_feature_is_active(self.context.get('request'), type(obj).__name__, obj.name)

    def get_id(self, obj):
        return '{}_{}'.format(type(obj).__name__.lower(), obj.id)

    class Meta:
        type_ = 'waffle'
