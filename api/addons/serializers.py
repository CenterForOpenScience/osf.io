from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField
from api.base.utils import absolute_reverse

class NodeAddonFolderSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'node_addon_folders'

    id = ser.CharField(source='provider', read_only=True)
    kind = ser.CharField(default='folder', read_only=True)
    name = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    folder_id = ser.CharField(read_only=True)

    links = LinksField({
        'children': 'get_absolute_url'
    })

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        addon_name = self.context['request'].parser_context['kwargs']['provider']

        return absolute_reverse(
            'nodes:node-addon-folders',
            kwargs={
                'node_id': node_id,
                'provider': addon_name
            },
            query_kwargs={
                'path': obj['path'],
                'folder_id': obj['folder_id']
            }
        )
