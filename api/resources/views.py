import logging

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.views import JSONAPIBaseView
from api.resources.permissions import ResourceDetailPermission
from api.resources.serializers import ResourceSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import Guid, OutcomeArtifact

logger = logging.getLogger(__name__)

class ResourceDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):

    permission_classes = (
        ResourceDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_REGISTRATION_RESOURCES]
    required_write_scopes = [CoreScopes.WRITE_REGISTRATION_RESOURCES]

    view_category = 'resources'
    view_name = 'resource-detail'

    serializer_class = ResourceSerializer

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)

    def get_object(self):
        try:
            return OutcomeArtifact.objects.get(_id=self.kwargs['resource_id'])
        except OutcomeArtifact.DoesNotExist:
            raise NotFound

    def get_permissions_proxy(self):
        return Guid.load(self.get_object().primary_resource_guid).referent
