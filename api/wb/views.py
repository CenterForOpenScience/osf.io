from rest_framework import generics, status, permissions as drf_permissions
from rest_framework.exceptions import NotFound

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


class MoveFileMetadata(JSONAPIBaseView, generics.CreateAPIView, WaterButlerMixin):
    """
    View for creating metadata for file move/copy in osfstorage.  Only WaterButler should talk to this endpoint.
    To move/copy a file, send a request to WB, and WB will call this view.
    """
    parser_classes = (HMACSignedParser,)

    serializer_class = WaterbutlerMetadataSerializer
    view_category = 'wb'
    view_name = 'metadata-move'
    node_lookup_url_kwarg = 'node_id'

    # Overrides CreateAPIView
    def get_object(self):
        return self.get_node(self.kwargs[self.node_lookup_url_kwarg])

    def get_node(self, node_id):
        node = get_object_or_error(
            AbstractNode,
            node_id,
            self.request,
            display_name='node'
        )
        if node.is_registration:
            raise NotFound
        return node

    # overrides CreateApiView
    def perform_create(self, serializer):
        source = serializer.validated_data.pop('source')
        destination = serializer.validated_data.pop('destination')
        name = destination.get('name')

        dest_node = self.get_node(node_id = destination.get('node'))

        try:
            source = OsfStorageFileNode.get(source, self.get_object())
        except OsfStorageFileNode.DoesNotExist:
            raise NotFound

        try:
             dest_parent = OsfStorageFolder.get(destination.get('parent'), dest_node)
        except OsfStorageFolder.DoesNotExist:
            raise NotFound
        return serializer.save(action='move', source=source, destination=dest_parent, name=name)

    def create(self, request, *args, **kwargs):
        response = super(MoveFileMetadata, self).create(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK
        return response
