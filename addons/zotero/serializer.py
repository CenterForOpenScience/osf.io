from addons.base.serializer import CitationsAddonSerializer

class ZoteroSerializer(CitationsAddonSerializer):
    addon_short_name = 'zotero'

    @property
    def serialized_node_settings(self):
        result = super(ZoteroSerializer, self).serialized_node_settings
        result['library'] = {
            'name': self.node_settings.fetch_library_name
        }
        return result

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        serialized_urls = super(ZoteroSerializer, self).addon_serialized_urls
        serialized_urls['libraries'] = node.api_url_for('{0}_library_list'.format(self.addon_short_name))
        return serialized_urls
