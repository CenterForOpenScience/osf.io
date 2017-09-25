from waffle.utils import get_setting
from waffle import flag_is_active
from rest_framework import serializers as ser

from api.base.serializers import (JSONAPISerializer, TypeField, RelationshipField)
from api.users.serializers import UserSerializer

class WaffleFlagSerializer(JSONAPISerializer):
    id = ser.CharField(source='name', required=True, help_text='The id of the flag, which is the same as the name')
    type = TypeField()
    name = ser.CharField(required=True, help_text='The name of the Flag')
    flag_default = ser.SerializerMethodField(help_text='Flag defaults for all flags')
    active = ser.SerializerMethodField()
    note = ser.CharField(required=False, allow_blank=True, help_text='Describe where the Flag is used.')

    def get_active(self, obj):
        """
        A flag is active if any of the criteria are true for the current user or request 
        """
        request = self.context.get("request")
        return flag_is_active(request, obj)

    def get_flag_default(self, obj):
        return get_setting('FLAG_DEFAULT')

    class Meta:
        type_ = 'waffle-flag',
