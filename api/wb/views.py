from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from osf.models import AbstractNode
from rest_framework.views import APIView
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.base.utils import get_object_or_error
from api.base.parsers import HMACSignedParser
from api.wb.serializers import (
    WaterbutlerMetadataSerializer
)

class FileMetadataView(APIView):
    """
    Mixin with common code for WB move/copy hooks
    """
    parser_classes = (HMACSignedParser,)
    serializer_class = WaterbutlerMetadataSerializer
    view_category = 'wb'
    node_lookup_url_kwarg = 'node_id'

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

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'view': self
        }

    def post(self, request, *args, **kwargs):
        serializer = WaterbutlerMetadataSerializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
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
            serializer.save(source=source, destination=dest_parent, name=name)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MoveFileMetadataView(FileMetadataView):
    """
    View for moving file metadata in OsfStorage.
    Only WaterButler should talk to this endpoint by sending a signed request.
    """

    view_name = 'metadata-move'

    # overrides FileMetadataView
    def post(self, request, *args, **kwargs):
        response = super(MoveFileMetadataView, self).post(request, *args, **kwargs)
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            return response
        response.status_code = status.HTTP_200_OK
        return response

    def perform_file_action(self, source, destination, name):
        return source.move_under(destination, name)


class CopyFileMetadataView(FileMetadataView):
    """
    View for copying file metadata in OsfStorage.
    Only WaterButler should talk to this endpoint by sending a signed request.
    """

    view_name = 'metadata-copy'

    def perform_file_action(self, source, destination, name):
        return source.copy_under(destination, name)
