from rest_framework import serializers as ser
from website import settings
from urlparse import urljoin

from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
)


class Scope(object):
    def __init__(self, id, scope):
        scope = scope or {}
        self.id = id
        self.description = scope.description
        self.is_public = scope.is_public

    def absolute_url(self):
        return urljoin(settings.API_DOMAIN, '/v2/scopes/{}/'.format(self.id))

class ScopeSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['id'])

    id = ser.CharField(read_only=True, source='name')
    description = ser.CharField(read_only=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'scopes'

    def get_absolute_url(self, obj):
        return obj.absolute_url()
