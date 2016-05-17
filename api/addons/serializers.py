from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField
from api.base.utils import absolute_reverse

class NodeAddonFolderSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'node_addon_folders'

    id = ser.CharField(read_only=True)
    kind = ser.CharField(default='folder', read_only=True)
    name = ser.CharField(read_only=True)
    folder_id = ser.CharField(source='id', read_only=True)
    path = ser.CharField(read_only=True)
    provider = ser.CharField(read_only=True)

    links = LinksField({
        'children': 'get_absolute_url',
        'root': 'get_root_folder',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-addon-folders',
            kwargs=self.context['request'].parser_context['kwargs'],
            query_kwargs={
                'path': obj['path'],
                'id': obj['id']
            }
        )

    def get_root_folder(self, obj):
        return absolute_reverse(
            'nodes:node-addon-folders',
            kwargs=self.context['request'].parser_context['kwargs'],
        )

class AddonSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'addon'

    id = ser.CharField(source='short_name', read_only=True)
    name = ser.CharField(source='full_name', read_only=True)
    description = ser.CharField(read_only=True)
    url = ser.CharField(read_only=True)
    categories = ser.ListField(read_only=True)

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'addons:addon-list',
            kwargs=self.context['request'].parser_context['kwargs'],
        )
