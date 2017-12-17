from rest_framework import generics, status, permissions as drf_permissions

from osf.models import AbstractNode
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.base.views import (
    WaterButlerMixin
)
from api.nodes.views import NodeMixin
from api.nodes.permissions import (
    ContributorOrPublic,
    ExcludeWithdrawals,
)
from api.wb.serializers import (
    WaterbutlerMetadataSerializer

)
from api.base.parsers import HMACSignedParser
from framework.auth.oauth_scopes import CoreScopes


class MoveFileMetadata(JSONAPIBaseView, generics.CreateAPIView, NodeMixin, WaterButlerMixin):
    """
    View for creating metadata for file move/copy in osfstorage.  Only WaterButler should talk to this endpoint.
    To move/copy a file, send a request to WB, and WB will call this view.
    """
    parser_classes = (HMACSignedParser,)

    serializer_class = WaterbutlerMetadataSerializer
    view_category = 'wb'
    view_name = 'metadata-move'

    # Overrides CreateAPIView
    def get_object(self):
        return self.get_node()

    # overrides CreateApiView
    def perform_create(self, serializer):
        source = serializer.validated_data.pop('source')
        destination = serializer.validated_data.pop('destination')
        dest_node = self.get_node(specific_node_id = destination['node'])
        source = OsfStorageFileNode.get(source, self.get_object())
        dest_parent = OsfStorageFolder.get(destination['parent'], dest_node)

        return serializer.save(action='move', source=source, destination=dest_parent, name=destination['name'])

    def create(self, request, *args, **kwargs):
        response = super(MoveFileMetadata, self).create(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK
        return response
