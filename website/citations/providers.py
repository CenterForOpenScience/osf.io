import abc
from rest_framework import status as http_status

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.exceptions import PermissionsError

from osf.models.external import ExternalAccount, ExternalProvider


class CitationsOauthProvider(ExternalProvider):

    _client = None

    @abc.abstractproperty
    def serializer(self):
        pass

    @abc.abstractmethod
    def _get_client(self):
        pass

    @abc.abstractmethod
    def _get_folders(self):
        pass

    @abc.abstractmethod
    def _verify_client_validity(self):
        pass

    @abc.abstractmethod
    def _folder_metadata(self, folder_id):
        pass

    @abc.abstractmethod
    def _citations_for_folder(self, folder_id):
        pass

    @abc.abstractmethod
    def _citations_for_user(self, folder_id):
        pass

    @property
    def client(self):
        """An API session with <provider_name>"""
        if not self._client:
            self._client = self._get_client()
            self._verify_client_validity()

        return self._client

    def citation_lists(self, extract_folder):
        """List of CitationList objects, derived from Mendeley folders"""

        folders = self._get_folders()
        # TODO: Verify OAuth access to each folder
        all_documents = self.serializer.serialized_root_folder

        serialized_folders = [
            extract_folder(each)
            for each in folders
        ]
        return [all_documents] + serialized_folders

    def get_list(self, list_id=None):
        """Get a single CitationList
        :param str list_id: ID for a folder. Optional.
        :return CitationList: CitationList for the folder, or for all documents
        """
        if not list_id or list_id == 'ROOT':
            return self._citations_for_user()

        return self._citations_for_folder(list_id)

class CitationsProvider(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def serializer(self):
        pass

    @abc.abstractproperty
    def provider_name(self):
        pass

    def check_credentials(self, node_addon):
        """Checkes validity of credentials"""
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
                for each in user.external_accounts.filter(provider=self.provider_name)
            ]
        }

    def set_config(self, node_addon, user, external_list_id, external_list_name, auth):
        """ Changes folder associated with addon and logs event"""
        # Ensure request has all required information
        # Tell the user's addon settings that this node is connecting
        node_addon.user_settings.grant_oauth_access(
            node=node_addon.owner,
            external_account=node_addon.external_account,
            metadata={'folder': external_list_id}
        )
        node_addon.user_settings.save()

        # update this instance
        node_addon.list_id = external_list_id
        node_addon.save()

        node_addon.owner.add_log(
            '{0}_folder_selected'.format(self.provider_name),
            params={
                'project': node_addon.owner.parent_id,
                'node': node_addon.owner._id,
                'folder_id': external_list_id,
                'folder_name': external_list_name,
            },
            auth=auth,
        )

    def add_user_auth(self, node_addon, user, external_account_id):
        """Adds authorization to a node
        if the user has authorization to grant"""
        external_account = ExternalAccount.load(external_account_id)

        if not user.external_accounts.filter(id=external_account.id).all():
            raise HTTPError(http_status.HTTP_403_FORBIDDEN)

        try:
            node_addon.set_auth(external_account, user)
        except PermissionsError:
            raise HTTPError(http_status.HTTP_403_FORBIDDEN)

        result = self.serializer(
            node_settings=node_addon,
            user_settings=user.get_addon(self.provider_name),
        ).serialized_node_settings
        result['validCredentials'] = self.check_credentials(node_addon)
        return {'result': result}

    def remove_user_auth(self, node_addon, user):
        """Removes authorization from a node """
        node_addon.deauthorize(auth=Auth(user))
        node_addon.reload()
        result = self.serializer(
            node_settings=node_addon,
            user_settings=user.get_addon(self.provider_name),
        ).serialized_node_settings

        return {'result': result}

    def widget(self, node_addon):
        """Serializes settting needed to build the widget"""
        ret = node_addon.config.to_json()
        ret.update({
            'complete': node_addon.complete,
            'list_id': node_addon.list_id,
        })
        return ret

    def _extract_folder(self, folder):
        """Returns serialization of citations folder """
        folder = self._folder_to_dict(folder)
        return {
            'name': folder['name'],
            'provider_list_id': folder['list_id'],
            'id': folder['id'],
            'parent_list_id': folder.get('parent_id', None)
        }

    @abc.abstractmethod
    def _folder_to_dict(self, data):
        pass

    def _folder_id(self, node_addon):
        return node_addon.list_id

    def citation_list(self, node_addon, user, list_id, show='all'):
        """Returns a list of citations"""
        attached_list_id = self._folder_id(node_addon)
        # Currently only being used by Mendeley. Zotero overrides this method.
        account_folders = node_addon.get_folders(show_root=True)

        # Folders with 'parent_list_id'==None are children of 'All Documents'
        for folder in account_folders:
            if not folder.get('parent_list_id'):
                folder['parent_list_id'] = 'ROOT'

        if user:
            node_account = node_addon.external_account
            user_is_owner = user.external_accounts.filter(id=node_account.id).exists()
        else:
            user_is_owner = False

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
                    raise HTTPError(http_status.HTTP_403_FORBIDDEN)
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
