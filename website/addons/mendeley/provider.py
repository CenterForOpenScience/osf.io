from website.addons.citations import provider
from .model import MendeleyNodeSettings
from website.addons.citations.utils import serialize_account, serialize_folder, serialize_urls

class MendeleyCitationsProvider(provider.CitationsProvider):

    def __init__(self):
        super(MendeleyCitationsProvider, self).__init__('mendeley')

    def _serialize_model(self, node_addon, user):
        ret = super(MendeleyNodeSettings, node_addon).to_json(user)
        ret.update({
            'listId': node_addon.mendeley_list_id,
            'accounts': self.user_accounts(user),
            'currentAccount': serialize_account(node_addon.external_account),
        })
        return ret

    def _serialize_urls(self, node_addon):
        # collects node_settings and oauth urls
        ret = serialize_urls(node_addon)

        node = node_addon.owner

        external_account = node_addon.external_account
        deauthorize = None
        if external_account:
            deauthorize = node.api_url_for('mendeley_remove_user_auth')

        specific = {
            'importAuth': node.api_url_for('mendeley_add_user_auth'),
            'folders': node.api_url_for('mendeley_citation_list'),
            'config': node.api_url_for('mendeley_set_config'),
            'deauthorize': deauthorize,
            'accounts': node.api_url_for('list_mendeley_accounts_user')
        }
        ret.update(specific)
        return ret

    def widget(self, node_addon):

        ret = super(MendeleyCitationsProvider, self).widget(node_addon)
        ret.update({
            'list_id': node_addon.mendeley_list_id
        })
        return ret

    def _extract_folder(self, data):
        return serialize_folder(
            data.name,
            list_id=data.json['id'],
            parent_id=data.json.get('parent_id'),
            id=data.json.get('id')
        )

    def _serialize_folder(self, folder, node_addon):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': node_addon.owner.api_url_for(
                    'mendeley_citation_list',
                    mendeley_list_id=folder['id']),
            },
        }

    def _folder_id(self, node_addon):

        return node_addon.mendeley_list_id
