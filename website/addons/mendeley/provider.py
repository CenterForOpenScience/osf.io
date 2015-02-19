import http

from framework.exceptions import HTTPError

from website.addons.citations import provider
from .model import AddonMendeleyNodeSettings
from website.addons.citations import utils


class MendeleyCitationsProvider(provider.CitationsProvider):

    def __init__(self):
        super(MendeleyCitationsProvider, self).__init__('mendeley')

    def _serialize_model(self, node_addon, user):
        ret = super(AddonMendeleyNodeSettings, node_addon).to_json(user)
        ret.update({
            'listId': node_addon.mendeley_list_id,
            'accounts': self.user_accounts(user),
            'currentAccount': utils.serialize_account(node_addon.external_account),
        })
        return ret

    def _serialize_urls(self, node_addon):
        ret = super(MendeleyCitationsProvider, self)._serialize_urls(node_addon)

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
        }
        ret.update(specific)
        return ret

    def set_config(self, node_addon, user, external_account_id, external_list_id):

        external_account = super(MendeleyCitationsProvider, self).set_config(
            node_addon, user, external_account_id, external_list_id
        )

        # associate the list with the node
        node_addon.set_target_folder(external_list_id)

        return {}

    def widget(self, node_addon):

        ret = super(MendeleyCitationsProvider, self).widget(node_addon)
        ret.update({
            'list_id': node_addon.mendeley_list_id
        })
        return ret

    def remove_user_auth(self, node_addon, user):

        return super(MendeleyCitationsProvider, self).remove_user_auth(
            node_addon, user
        )

    def citation_list(self, node_addon, user, list_id, show='all'):

        attached_list_id = node_addon.mendeley_list_id
        account_folders = node_addon.api.citation_lists

        # Folders with 'parent_list_id'==None are children of 'All Documents'
        for folder in account_folders:
            if folder.get('parent_list_id') is None:
                folder['parent_list_id'] = 'ROOT'

        node_account = node_addon.external_account
        user_accounts = [
            account for account in user.external_accounts
            if account.provider == 'mendeley'
        ]
        user_is_owner = node_account in user_accounts

        # verify this list is the attached list or its descendant
        if not user_is_owner and (list_id != attached_list_id and attached_list_id is not None):
            folders = {
                (each['provider_list_id'] or 'ROOT'): each
                for each in account_folders
            }
            if list_id is None:
                ancestor_id = 'ROOT'
            else:
                ancestor_id = folders[list_id].get('parent_list_id')

            while ancestor_id != attached_list_id:
                if ancestor_id is '__':
                    raise HTTPError(http.FORBIDDEN)
                ancestor_id = folders[ancestor_id].get('parent_list_id')

        contents = []
        if list_id is None:
            contents = node_addon.api.get_root_folder()
        else:
            if show in ('all', 'folders'):
                contents += [
                    {
                        'data': each,
                        'kind': 'folder',
                        'name': each['name'],
                        'id': each['id'],
                        'urls': {
                            'fetch': node_addon.owner.api_url_for(
                                'mendeley_citation_list',
                                mendeley_list_id=each['id']),
                        },
                    }
                    for each in account_folders
                    if each.get('parent_list_id') == list_id
                ]

            if show in ('all', 'citations'):
                contents += [
                    {
                        'csl': each,
                        'kind': 'file',
                        'id': each['id'],
                    }
                    for each in node_addon.api.get_list(list_id)
                ]

        return {
            'contents': contents
        }
