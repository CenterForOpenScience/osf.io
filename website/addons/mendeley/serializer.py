from website.addons.base.serializer import CitationsAddonSerializer

class MendeleySerializer(CitationsAddonSerializer):

    def __init__(self, addon_node_settings, user):
        super(MendeleySerializer, self).__init__(addon_node_settings, user, 'mendeley')

    '''
    @property
    def serialized_node_settings(self):
        ret = self.addon_node_settings.to_json(self.user)
        ret.update({
            'listId': self.addon_node_settings.mendeley_list_id,
            'accounts': self.user_accounts,
            'currentAccount': self.serialized_account,
        })
        return ret
    '''

    def serialize_folder(self, folder):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': self.addon_node_settings.owner.api_url_for(
                    'citation_list',
                    mendeley_list_id=folder['id']
                ),
            },
        }

    @property
    def addon_serialized_urls(self):
        node = self.addon_node_settings.owner

        return {
            'importAuth': node.api_url_for('mendeley_add_user_auth'),
            'folders': node.api_url_for('mendeley_citation_list'),
            'config': node.api_url_for('mendeley_set_config'),
            'deauthorize': node.api_url_for('mendeley_remove_user_auth'),
        }
