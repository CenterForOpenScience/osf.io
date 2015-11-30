from website.addons.base.serializer import CitationsAddonSerializer

class MendeleySerializer(CitationsAddonSerializer):

    addon_short_name = 'mendeley'

    def serialize_folder(self, folder):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': self.node_settings.owner.api_url_for(
                    'mendeley_citation_list',
                    mendeley_list_id=folder['id']
                ),
            },
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'importAuth': node.api_url_for('mendeley_add_user_auth'),
            'folders': node.api_url_for('mendeley_citation_list'),
            'config': node.api_url_for('mendeley_set_config'),
            'deauthorize': node.api_url_for('mendeley_remove_user_auth'),
            'accounts': node.api_url_for('mendeley_get_user_accounts'),
        }
