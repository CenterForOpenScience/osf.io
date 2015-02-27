import abc
import httplib as http

from framework.exceptions import HTTPError
from framework.exceptions import PermissionsError

from website.oauth.models import ExternalAccount

from . import utils

class CitationsProvider(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, provider_name):

        self.provider_name = provider_name

    @abc.abstractmethod
    def _serialize_urls(self, node_addon):

        return {}

    @abc.abstractmethod
    def _serialize_model(self, node_addon, user):

        return {}

    def serialize_settings(self, node_settings, current_user):
        """Serializes parameters for building UI for widget and settings pages
        """
        node_account = node_settings.external_account
        user_accounts = [account for account in current_user.external_accounts
                         if account.provider == self.provider_name]

        user_settings = current_user.get_addon(self.provider_name)

        user_settings = current_user.get_addon(self.provider_name)
        user_has_auth = bool(user_settings and user_accounts)

        node_has_auth = node_settings.has_auth
        user_is_owner = (node_has_auth and (node_account in user_accounts)) or bool(len(user_accounts))

        result = {
            'nodeHasAuth': node_has_auth,
            'userIsOwner': user_is_owner,
            'userHasAuth': user_has_auth,
            'urls': self._serialize_urls(node_settings),
            'validCredentials': True
        }

        if node_account is not None:
            result['folder'] = node_settings.selected_folder_name
            result['ownerName'] = node_account.display_name

        result.update(self._serialize_model(node_settings, current_user))
        return result

    def user_accounts(self, user):
        """ Gets a list of the accounts authorized by 'user' """
        return {
            'accounts': [
                utils.serialize_account(each)
                for each in user.external_accounts
                if each.provider == self.provider_name
            ]
        }

    def set_config(self, node_addon, user, external_list_id):
        # Ensure request has all required information

        node_addon.set_target_folder(external_list_id)

    def add_user_auth(self, node_addon, user, external_account_id):

        external_account = ExternalAccount.load(external_account_id)

        if external_account not in user.external_accounts:
            raise HTTPError(http.FORBIDDEN)

        try:
            node_addon.set_auth(external_account, user)
        except PermissionsError:
            raise HTTPError(http.FORBIDDEN)

        result = self.serialize_settings(node_addon, user)
        return {'result': result}

    def remove_user_auth(self, node_addon, user):

        node_addon.clear_auth()
        node_addon.reload()
        result = self.serialize_settings(node_addon, user)
        return {'result': result}

    def widget(self, node_addon):

        ret = node_addon.config.to_json()
        ret.update({
            'complete': node_addon.complete,
        })
        return ret

    @abc.abstractmethod
    def _extract_folder(self, data):

        return {}

    @abc.abstractmethod
    def _serialize_folder(self, folder):

        return {}

    def _serialize_citation(self, citation):

        return {
            'csl': citation,
            'kind': 'file',
            'id': citation['id'],
        }

    @abc.abstractmethod
    def _folder_id(self):

        return None

    def citation_list(self, node_addon, user, list_id, show='all'):

        attached_list_id = self._folder_id(node_addon)
        account_folders = node_addon.api.citation_lists(self._extract_folder)

        # Folders with 'parent_list_id'==None are children of 'All Documents'
        for folder in account_folders:
            if folder.get('parent_list_id') is None:
                folder['parent_list_id'] = 'ROOT'

        node_account = node_addon.external_account
        user_accounts = [
            account for account in user.external_accounts
            if account.provider == self.provider_name
        ] if user else []
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
            contents = [node_addon.root_folder]
        else:
            if show in ('all', 'folders'):
                contents += [
                    self._serialize_folder(each, node_addon)
                    for each in account_folders
                    if each.get('parent_list_id') == list_id
                ]

            if show in ('all', 'citations'):
                contents += [
                    self._serialize_citation(each)
                    for each in node_addon.api.get_list(list_id)
                ]

        return {
            'contents': contents
        }
