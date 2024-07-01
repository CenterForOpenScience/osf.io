from addons.base.serializer import CitationsAddonSerializer

class ZoteroSerializer(CitationsAddonSerializer):
    addon_short_name = 'zotero'

    @property
    def serialized_node_settings(self):
        result = super().serialized_node_settings
        result['library'] = {
            'name': self.node_settings.fetch_library_name
        }
        return result

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        serialized_urls = super().addon_serialized_urls
        serialized_urls['libraries'] = node.api_url_for(f'{self.addon_short_name}_library_list')
        return serialized_urls
