import abc
import httplib as http

from framework.exceptions import HTTPError
from framework.exceptions import PermissionsError

from website.oauth.models import ExternalAccount

class CitationsProvider(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, provider_name):
        self.provider_name = provider_name

    @abc.abstractproperty
    def serializer(self):
        pass

    def check_credentials(self, node_addon):
        valid = True
        if node_addon.api.account:
            try:
                node_addon.api.client
            except HTTPError as err:
                if err.code == 403:
                    valid = False
                else:
                    raise err

        return valid

    def user_accounts(self, user):
        """ Gets a list of the accounts authorized by 'user' """
        return {
            'accounts': [
                self.serializer(
                    user_settings=user.get_addon(self.provider_name) if user else None
                ).serialize_account(each)
                for each in user.external_accounts
                if each.provider == self.provider_name
            ]
        }

    def set_config(self, node_addon, user, external_list_id, external_list_name, auth):
        # Ensure request has all required information
        node_addon.set_target_folder(external_list_id, external_list_name, auth)

    def add_user_auth(self, node_addon, user, external_account_id):

        external_account = ExternalAccount.load(external_account_id)

        if external_account not in user.external_accounts:
            raise HTTPError(http.FORBIDDEN)

        try:
            node_addon.set_auth(external_account, user)
        except PermissionsError:
            raise HTTPError(http.FORBIDDEN)

        result = self.serializer(
            node_settings=node_addon,
            user_settings=user.get_addon(self.provider_name),
        ).serialized_node_settings
        result['validCredentials'] = self.check_credentials(node_addon)
        return {'result': result}

    def remove_user_auth(self, node_addon, user):

        node_addon.clear_auth()
        node_addon.reload()
        result = self.serializer(
            node_settings=node_addon,
            user_settings=user.get_addon(self.provider_name),
        ).serialized_node_settings
        return {'result': result}

    def widget(self, node_addon):

        ret = node_addon.config.to_json()
        ret.update({
            'complete': node_addon.complete,
        })
        return ret

    def _extract_folder(self, folder):
        folder = self._folder_to_dict(folder)
        ret = {
            'name': folder['name'],
            'provider_list_id': folder['list_id'],
            'id': folder['id'],
        }
        if folder['parent_id']:
            ret['parent_list_id'] = folder['parent_id']
        return ret

    @abc.abstractmethod
    def _folder_to_dict(self, data):
        pass

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
            user_settings = user.get_addon(self.provider_name) if user else None
            if show in ('all', 'folders'):
                contents += [
                    self.serializer(
                        node_settings=node_addon,
                        user_settings=user_settings,
                    ).serialize_folder(each)
                    for each in account_folders
                    if each.get('parent_list_id') == list_id
                ]

            if show in ('all', 'citations'):
                contents += [
                    self.serializer(
                        node_settings=node_addon,
                        user_settings=user_settings,
                    ).serialize_citation(each)
                    for each in node_addon.api.get_list(list_id)
                ]

        return {
            'contents': contents
        }
