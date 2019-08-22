from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response

from osf.models import Guid
from rest_framework.views import APIView
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.base.parsers import HMACSignedParser
from api.wb.serializers import (
    WaterbutlerMetadataSerializer,
)

from api.caching.tasks import update_storage_usage


class FileMetadataView(APIView):
    """
    Mixin with common code for WB move/copy hooks
    """
    parser_classes = (HMACSignedParser,)
    serializer_class = WaterbutlerMetadataSerializer
    view_category = 'wb'
    target_lookup_url_kwarg = 'target_id'

    def get_object(self):
        return self.get_target(self.kwargs[self.target_lookup_url_kwarg])

    def get_target(self, target_id):
        guid = Guid.load(target_id)
        if not guid:
            raise NotFound
        target = guid.referent
        if getattr(target, 'is_registration', False) and not getattr(target, 'archiving', False):
            raise ValidationError('Registrations cannot be changed.')
        return target

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'view': self,
        }

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            source = serializer.validated_data.pop('source')
            destination = serializer.validated_data.pop('destination')
            name = destination.get('name')
            dest_target = self.get_target(target_id=destination.get('target'))
            try:
                source = OsfStorageFileNode.get(source, self.get_object())
            except OsfStorageFileNode.DoesNotExist:
                raise NotFound

            try:
                dest_parent = OsfStorageFolder.get(destination.get('parent'), dest_target)
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
        dest_target = destination.target
        source_target = source.target
        ret = source.move_under(destination, name)

        if dest_target != source_target:
            update_storage_usage(source.target)
            update_storage_usage(destination.target)

        return ret


class CopyFileMetadataView(FileMetadataView):
    """
    View for copying file metadata in OsfStorage.
    Only WaterButler should talk to this endpoint by sending a signed request.
    """

    view_name = 'metadata-copy'

    def perform_file_action(self, source, destination, name):
        ret = source.copy_under(destination, name)
        update_storage_usage(destination.target)
        return ret
