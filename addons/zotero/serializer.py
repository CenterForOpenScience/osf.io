from addons.base.serializer import CitationsAddonSerializer

class ZoteroSerializer(CitationsAddonSerializer):
    addon_short_name = 'zotero'

    @property
    def serialized_node_settings(self):
        result = super(ZoteroSerializer, self).serialized_node_settings
        result['library'] = {
            'name': self.node_settings.fetch_library_name
        }
        result['groups'] = self.node_settings.fetch_groups
        return result
