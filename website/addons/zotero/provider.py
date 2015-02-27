# -*- coding: utf-8 -*-
from website.addons.citations import provider

from .model import ZoteroNodeSettings
from website.addons.citations.utils import serialize_account, serialize_folder, serialize_urls

class ZoteroCitationsProvider(provider.CitationsProvider):

    def __init__(self):
        super(ZoteroCitationsProvider, self).__init__('zotero')

    def _serialize_model(self, node_addon, user):
        ret = super(ZoteroNodeSettings, node_addon).to_json(user)
        ret.update({
            'listId': node_addon.zotero_list_id,
            'accounts': self.user_accounts(user),
            'currentAccount': serialize_account(node_addon.external_account),
        })
        return ret

    def _serialize_urls(self, node_addon):
        # collects node_settings and oauth urls
        ret = serialize_urls(node_addon)

        node = node_addon.owner

        external_account = node_addon.external_account

        urls = {
            'importAuth': node.api_url_for('zotero_add_user_auth'),
            'folders': node.api_url_for('zotero_citation_list'),
            'config': node.api_url_for('zotero_set_config'),
            'accounts': node.api_url_for('list_zotero_accounts_user'),
        }

        if external_account:
            urls['deauthorize'] = node.api_url_for(
                'zotero_remove_user_auth'
            )
            urls['owner'] = external_account.profile_url

        ret.update(urls)
        return ret

    def widget(self, node_addon):

        ret = super(ZoteroCitationsProvider, self).widget(node_addon)
        ret.update({
            'list_id': node_addon.zotero_list_id
        })
        return ret

    def _extract_folder(self, data):
        return serialize_folder(
            data['data'].get('name'),
            list_id=data['data'].get('key'),
            parent_id=data['data'].get('parentCollection'),
            id=data['data'].get('key')
        )

    def _serialize_folder(self, folder, node_addon):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': node_addon.owner.api_url_for(
                    'zotero_citation_list',
                    zotero_list_id=folder['id']),
            },
        }

    def _folder_id(self, node_addon):

        return node_addon.zotero_list_id
