from rest_framework import generics, status
from rest_framework.exceptions import NotFound

from osf.models import AbstractNode
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.base.utils import get_object_or_error
from api.base.parsers import HMACSignedParser
from api.wb.serializers import (
    WaterbutlerMetadataSerializer
)

class FileMetadataMixin(generics.CreateAPIView):
    """
    Mixin with common code for WB move/copy hooks
    """
    parser_classes = (HMACSignedParser,)
    serializer_class = WaterbutlerMetadataSerializer
    view_category = 'wb'
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

    def perform_create(self, serializer, action):
        source = serializer.validated_data.pop('source')
        destination = serializer.validated_data.pop('destination')
        name = destination.get('name')
        dest_node = self.get_node(node_id=destination.get('node'))

        try:
            source = OsfStorageFileNode.get(source, self.get_object())
        except OsfStorageFileNode.DoesNotExist:
            raise NotFound

        try:
            dest_parent = OsfStorageFolder.get(destination.get('parent'), dest_node)
        except OsfStorageFolder.DoesNotExist:
            raise NotFound
        return serializer.save(action=action, source=source, destination=dest_parent, name=name)


class MoveFileMetadataView(FileMetadataMixin):
    """
    View for moving file metadata in OsfStorage.
    Only WaterButler should talk to this endpoint by sending a signed request.
    """

    view_name = 'metadata-move'

    # overrides CreateApiView
    def perform_create(self, serializer):
        return super(MoveFileMetadataView, self).perform_create(serializer, 'move')

    # overrides CreateApiView
    def create(self, request, *args, **kwargs):
        response = super(MoveFileMetadataView, self).create(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK
        return response


class CopyFileMetadataView(FileMetadataMixin):
    """
    View for copying file metadata in OsfStorage.
    Only WaterButler should talk to this endpoint by sending a signed request.
    """

    view_name = 'metadata-copy'

    # overrides CreateApiView
    def perform_create(self, serializer):
        return super(CopyFileMetadataView, self).perform_create(serializer, 'copy')

    # overrides CreateApiView
    def create(self, request, *args, **kwargs):
        response = super(CopyFileMetadataView, self).create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        return response
