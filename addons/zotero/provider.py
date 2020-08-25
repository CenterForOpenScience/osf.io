# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from framework.exceptions import HTTPError
from website.citations.providers import CitationsProvider
from addons.zotero.serializer import ZoteroSerializer

class ZoteroCitationsProvider(CitationsProvider):
    serializer = ZoteroSerializer
    provider_name = 'zotero'

    def _folder_to_dict(self, data):
        return dict(
            name=data['data'].get('name'),
            list_id=data['data'].get('key'),
            parent_id=data['data'].get('parentCollection'),
            id=data['data'].get('key'),
        )

    def widget(self, node_addon):
        """
        Serializes setting needed to build the widget
        library_id added specifically for zotero
        """
        ret = super(ZoteroCitationsProvider, self).widget(node_addon)
        ret.update({
            'library_id': node_addon.library_id
        })
        return ret

    def set_config(self, node_addon, user, external_list_id, external_list_name, auth, external_library_id=None, external_library_name=None):
        """ Changes folder associated with addon and logs event"""
        # Ensure request has all required information
        # Tell the user's addon settings that this node is connecting
        metadata = {'folder': external_list_id}
        if external_library_id:
            metadata['library'] = external_library_id
            metadata['folder'] = None
        node_addon.user_settings.grant_oauth_access(
            node=node_addon.owner,
            external_account=node_addon.external_account,
            metadata=metadata
        )
        node_addon.user_settings.save()

        # update this instance
        node_addon.list_id = external_list_id
        if external_library_id:
            node_addon.library_id = external_library_id
            node_addon.list_id = None
        node_addon.save()

        if external_library_id:
            node_addon.owner.add_log(
                '{0}_library_selected'.format(self.provider_name),
                params={
                    'project': node_addon.owner.parent_id,
                    'node': node_addon.owner._id,
                    'library_name': external_library_name,
                    'library_id': external_library_id
                },
                auth=auth,
            )
        else:
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

    def citation_list(self, node_addon, user, list_id, show='all'):
        """Returns a list of citations"""
        attached_list_id = self._folder_id(node_addon)
        attached_library_id = getattr(node_addon, 'library_id', None)
        account_folders = node_addon.get_folders(path=attached_library_id)
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
                    for each in node_addon.api.get_list(list_id=list_id, library_id=attached_library_id)
                ]

        return {
            'contents': contents
        }
