from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, LinksField, JSONAPIHyperlinkedIdentityField, IDField
)

class NodeAddonSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'user_addons'

    id = IDField(source='_id')
    short_name = ser.SerializerMethodField()
    full_name = ser.SerializerMethodField()

    # TODO addon config

    def get_short_name(self, instance):
        return instance.config.short_name

    def get_full_name(self, instance):
        return instance.config.full_name
