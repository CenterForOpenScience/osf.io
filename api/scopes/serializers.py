from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
)

# With this API version, scopes are a M2M field on ApiOAuth2PersonalToken, and
# serialized as relationship.
SCOPES_RELATIONSHIP_VERSION = '2.17'

class ScopeSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['id'])

    id = ser.CharField(read_only=True, source='name')
    description = ser.CharField(read_only=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'scopes'

    def get_absolute_url(self, obj):
        return obj.absolute_url()
