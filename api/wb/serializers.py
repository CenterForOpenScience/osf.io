from django.db import IntegrityError

from api.base.serializers import (IDField,
                                  TypeField,)

from api.files.serializers import FileSerializer
from rest_framework import serializers as ser
from rest_framework import exceptions
from website.files import exceptions as file_exceptions


class NodeProviderFileMetadataCreateSerializer(FileSerializer):
    action_choices = ['move', 'copy']
    action_choices_string = ', '.join(["'{}'".format(choice) for choice in action_choices])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    action = ser.ChoiceField(choices=action_choices, write_only=True, help_text='Choices: ' + action_choices_string)
    checkout = ser.CharField(read_only=True)
    destination_node = ser.CharField(allow_null=True, required=False, write_only=True, help_text='Id of destination node. If none, the node of the source will be used.')
    destination_parent = ser.CharField(allow_null=True, write_only=True, help_text='Id of destination folder. Null if moving to top level of osfstorage.')
    name = ser.CharField(allow_null=True, required=False, help_text='New file name if renaming. If none, will use current file name.')
    source = ser.CharField(write_only=True, help_text='Id of file you are copying.')

    def create(self, validated_data):
        source_node = self.context['view'].get_node()
        provider_id = self.context['view'].get_provider_id()
        destination_node_id = validated_data.pop('destination_node', '')
        destination_node = self.context['view'].get_node(specific_node_id=destination_node_id) if destination_node_id else source_node

        source = self.context['view'].get_file_object(source_node, validated_data.pop('source', ''), provider_id, check_object_permissions=False)
        destination = self.context['view'].get_file_object(destination_node, (validated_data.pop('destination_parent', '') or '') + '/', provider_id, check_object_permissions=False)

        action = validated_data.pop('action', '')
        name = validated_data.pop('name', source.name)

        try:
            # Current actions are only move and copy
            return source.copy_under(destination, name) if action == 'copy' else source.move_under(destination, name)
        except IntegrityError:
            raise exceptions.ValidationError('File already exists with this name.')
        except file_exceptions.FileNodeIsQuickFilesNode:
            raise exceptions.ValidationError('Cannot {} file as it is in a quickfiles node.'.format(action))
        except file_exceptions.FileNodeCheckedOutError:
            raise exceptions.ValidationError('Cannot move file as it is checked out.')
        except file_exceptions.FileNodeIsPrimaryFile:
            raise exceptions.ValidationError('Cannot move file as it is the primary file of preprint.')

    class Meta:
        type_ = 'file_metadata'
