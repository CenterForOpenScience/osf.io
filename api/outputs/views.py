import logging

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.views import JSONAPIBaseView
from api.outputs.permissions import OutputDetailPermission
from api.outputs.serializers import OutputSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import Guid, OutcomeArtifact

logger = logging.getLogger(__name__)

class OutputDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):

    permission_classes = (
        OutputDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_REGISTRATION_OUTPUTS]
    required_write_scopes = [CoreScopes.WRITE_REGISTRATION_OUTPUTS]

    view_category = 'outputs'
    view_name = 'output-detail'

    serializer_class = OutputSerializer

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)

    def get_object(self):
        try:
            return OutcomeArtifact.objects.get(_id=self.kwargs['output_id'])
        except OutcomeArtifact.DoesNotExist:
            raise NotFound

    def get_permissions_proxy(self):
        return Guid.load(self.get_object().primary_resource_guid).referent
