from django.db import IntegrityError

from api.base.serializers import (IDField,
                                  TypeField,)
from osf.models import AbstractNode
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.files.serializers import FileSerializer
from rest_framework import serializers as ser
from rest_framework import exceptions
from website.files import exceptions as file_exceptions


class NodeProviderFileMetadataCreateSerializer(ser.Serializer):
    source = ser.CharField(help_text='Id of file you are copying.')
    destination = ser.DictField(child=ser.CharField())

    def create(self, validated_data):
        source = validated_data.pop('source')
        destination = validated_data.pop('destination')

        dest_node = AbstractNode.load(destination.get('node'))
        source = OsfStorageFileNode.get(source, validated_data.get('source_node'))
        dest_parent = OsfStorageFolder.get(destination['parent'], dest_node)

        action = validated_data.pop('action', '')
        name = destination.get('name', source.name)

        try:
            # Current actions are only move and copy
            source.copy_under(dest_parent, name) if action == 'copy' else source.move_under(dest_parent, name)
            return {'source':source, 'destination': destination}
        except IntegrityError:
            raise exceptions.ValidationError('File already exists with this name.')
        except file_exceptions.FileNodeCheckedOutError:
            raise exceptions.ValidationError('Cannot move file as it is checked out.')
        except file_exceptions.FileNodeIsPrimaryFile:
            raise exceptions.ValidationError('Cannot move file as it is the primary file of preprint.')

    class Meta:
        type_ = 'file_metadata'
