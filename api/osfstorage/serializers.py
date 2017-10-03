from django.db import IntegrityError

from rest_framework import serializers as ser
from rest_framework import exceptions

from osf.models import AbstractNode
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.base.serializers import JSONAPISerializer, IDField, TypeField


class OsfStorageSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    parent= ser.CharField(write_only=True, help_text="Id of containing destination folder for file")
    node = ser.CharField(write_only=True, help_text="Id of source node")
    source = ser.CharField(write_only=True, help_text="Id of file you are copying")
    action=ser.CharField(write_only=True, help_text="Copy or move, need to make this choicefield")

    def create(self, validated_data):
        import pdb; pdb.set_trace()
        node_id = validated_data.pop('node', '')
        source_id = validated_data.pop('source', '')
        parent_id = validated_data.pop('parent', '')
        action = validated_data.pop('action', '')
        try:
            node = AbstractNode.objects.get(guids___id=node_id)
            if node.is_registration:
                raise exceptions.ValidationError('Node cannot be a registration.')
            if not(node.get_addon('osfstorage')):
                raise exceptions.ValidationError('Node must have OSFStorage Addon.')
        except AbstractNode.DoesNotExist:
            raise exceptions.NotFound('Cannot find node.')
        try:
            source = OsfStorageFileNode.get(source_id, node.id)
        except OsfStorageFileNode.DoesNotExist:
            raise exceptions.NotFound('Cannot find file.')

        try:
            destination = OsfStorageFolder.get(parent_id, node.id)
        except OsfStorageFolder.DoesNotExist:
            raise exceptions.NotFound('Cannot find folder.')

        if action == 'copy':
            try:
                return source.copy_under(destination, name=source.name)
            except IntegrityError:
                raise exceptions.ValidationError('File already exists with this name.')



    class Meta:
        type_ = 'file_metadata'
