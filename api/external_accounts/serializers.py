from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, LinksField, JSONAPIHyperlinkedIdentityField, IDField
)

from website.addons.base import AddonOAuthUserSettingsBase

class ExternalAccountSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'external_accounts'

    id = IDField(source='_id')
    provider = ser.SerializerMethodField()

    def get_provider(self, instance):
        if isinstance(instance, AddonOAuthUserSettingsBase):
            return instance.provider
        else:
            return instance.config.short_name
