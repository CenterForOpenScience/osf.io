from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, TypeField
from api.base.waffle_decorators import waffle_feature_is_active
from waffle.models import Flag, Sample, Switch


class BaseWaffleSerializer(JSONAPISerializer):
    id = ser.SerializerMethodField()
    type = TypeField()
    name = ser.CharField(required=True, help_text='The name of the waffle object')
    active = ser.SerializerMethodField()
    note = ser.CharField(required=False, allow_blank=True, help_text='Describe where the waffle object is used.')

    def get_type(self, obj):
        return type(obj).__name__.lower()

    def get_active(self, obj):
        """
        Use waffle_feature_is_active helper to determine if waffle flag, sample, or switch is active
        """
        return waffle_feature_is_active(self.context.get('request'), self.get_type(obj), obj.name)

    def get_id(self, obj):
        return '{}_{}'.format(self.get_type(obj), obj.id)

    class Meta:
        type_ = 'waffle'


class FlagSerializer(BaseWaffleSerializer):
    class Meta:
        type_ = 'flag'


class SampleSerializer(BaseWaffleSerializer):
    class Meta:
        type_ = 'sample'


class SwitchSerializer(BaseWaffleSerializer):
    class Meta:
        type_ = 'switch'


class WaffleSerializer(JSONAPISerializer):

    def to_representation(self, data, envelope='data'):

        if isinstance(data, Flag):
            serializer = FlagSerializer(data, context=self.context)
            return FlagSerializer.to_representation(serializer, data)

        if isinstance(data, Sample):
            serializer = SampleSerializer(data, context=self.context)
            return SampleSerializer.to_representation(serializer, data)

        if isinstance(data, Switch):
            serializer = SwitchSerializer(data, context=self.context)
            return SwitchSerializer.to_representation(serializer, data)

        return None

    class Meta:
        type_ = 'waffle'
