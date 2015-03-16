from website.addons.base.serializer import OAuthAddonSerializer


class BoxSerializer(OAuthAddonSerializer):

    def serialize_folder(self, folder):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': self.node_settings.owner.api_url_for(
                    'box_folder_list',
                    folderId=folder['id']
                ),
            },
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'importAuth': node.api_url_for('box_add_user_auth'),
            'folders': node.api_url_for('box_folder_list'),
            'config': node.api_url_for('box_set_config'),
            'deauthorize': node.api_url_for('box_remove_user_auth'),
            'accounts': node.api_url_for('box_get_user_settings'),
        }
