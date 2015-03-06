from website.addons.base.serializer import CitationsAddonSerializer

class MendeleySerializer(CitationsAddonSerializer):

    def __init__(self, addon_node_settings, user):
        super(MendeleySerializer, self).__init__(addon_node_settings, user, 'mendeley')

    @property
    def serialized_model(self):
        ret = self.addon_node_settings.to_json(self.user)
        ret.update({
            'listId': self.addon_node_settings.mendeley_list_id,
            'accounts': self.user_accounts,
            'currentAccount': self.serialized_account,
        })
        return ret

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
            }
        }
