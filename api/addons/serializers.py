from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField
from api.base.utils import absolute_reverse
from api.base.versioning import get_kebab_snake_case_field

class NodeAddonFolderSerializer(JSONAPISerializer):
    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'node-addon-folders')

    id = ser.CharField(read_only=True)
    kind = ser.CharField(default='folder', read_only=True)
    name = ser.CharField(read_only=True)
    folder_id = ser.CharField(source='id', read_only=True)
    path = ser.CharField(read_only=True)
    provider = ser.CharField(source='addon', read_only=True)

    links = LinksField({
        'children': 'get_absolute_url',
        'root': 'get_root_folder',
    })

    def get_absolute_url(self, obj):
        if obj['addon'] in ('figshare', 'github', 'mendeley'):
            # These addons don't currently support linking anything other
            # than top-level objects.
            return

        return absolute_reverse(
            'nodes:node-addon-folders',
            kwargs=self.context['request'].parser_context['kwargs'],
            query_kwargs={
                'path': obj['path'],
                'id': obj['id'],
            },
        )

    def get_root_folder(self, obj):
        return absolute_reverse(
            'nodes:node-addon-folders',
            kwargs=self.context['request'].parser_context['kwargs'],
        )

class AddonSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'categories',
    ])

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
