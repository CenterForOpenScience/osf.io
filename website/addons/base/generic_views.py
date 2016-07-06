"""Generic add-on view factories"""
# -*- coding: utf-8 -*-
import httplib as http

from flask import request

from framework.exceptions import HTTPError, PermissionsError
from framework.auth.decorators import must_be_logged_in

from website.oauth.models import ExternalAccount

from website.util import permissions, rubeus
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)

def import_auth(addon_short_name, Serializer):
    @must_have_addon(addon_short_name, 'user')
    @must_have_addon(addon_short_name, 'node')
    @must_have_permission(permissions.WRITE)
    def _import_auth(auth, node_addon, user_addon, **kwargs):
        """Import add-on credentials from the currently logged-in user to a node.
        """
        external_account = ExternalAccount.load(
            request.json['external_account_id']
        )

        if external_account not in user_addon.external_accounts:
            raise HTTPError(http.FORBIDDEN)

        try:
            node_addon.set_auth(external_account, user_addon.owner)
        except PermissionsError:
            raise HTTPError(http.FORBIDDEN)

        node_addon.save()

        return {
            'result': Serializer().serialize_settings(node_addon, auth.user),
            'message': 'Successfully imported access token from profile.',
        }
    _import_auth.__name__ = '{0}_import_auth'.format(addon_short_name)
    return _import_auth

def account_list(addon_short_name, Serializer):
    @must_be_logged_in
    def _account_list(auth):
        user_settings = auth.user.get_addon(addon_short_name)
        serializer = Serializer(user_settings=user_settings)
        return serializer.serialized_user_settings
    _account_list.__name__ = '{0}_account_list'.format(addon_short_name)
    return _account_list

def folder_list(addon_short_name, addon_full_name, get_folders):
    @must_have_addon(addon_short_name, 'node')
    @must_be_addon_authorizer(addon_short_name)
    def _folder_list(node_addon, **kwargs):
        """Returns a list of folders"""
        if not node_addon.has_auth:
            raise HTTPError(http.FORBIDDEN)

        folder_id = request.args.get('folderId')
        return get_folders(node_addon, folder_id)
    _folder_list.__name__ = '{0}_folder_list'.format(addon_short_name)
    return _folder_list

def root_folder(addon_short_name):
    def _root_folder(node_settings, auth, **kwargs):
        """Return the Rubeus/HGrid-formatted response for the root folder only."""
        # Quit if node settings does not have authentication
        if not node_settings.has_auth or not node_settings.folder_id:
            return None
        node = node_settings.owner
        root = rubeus.build_addon_root(
            node_settings=node_settings,
            name=node_settings.fetch_folder_name(),
            permissions=auth,
            nodeUrl=node.url,
            nodeApiUrl=node.api_url,
            private_key=kwargs.get('view_only', None),
        )
        return [root]
    _root_folder.__name__ = '{0}_root_folder'.format(addon_short_name)
    return _root_folder


def get_config(addon_short_name, Serializer):
    @must_be_logged_in
    @must_have_addon(addon_short_name, 'node')
    @must_be_valid_project
    @must_have_permission(permissions.WRITE)
    def _get_config(node_addon, auth, **kwargs):
        """API that returns the serialized node settings."""
        return {
            'result': Serializer().serialize_settings(
                node_addon,
                auth.user
            )
        }
    _get_config.__name__ = '{0}_get_config'.format(addon_short_name)
    return _get_config

def set_config(addon_short_name, addon_full_name, Serializer, set_folder):
    @must_not_be_registration
    @must_have_addon(addon_short_name, 'user')
    @must_have_addon(addon_short_name, 'node')
    @must_be_addon_authorizer(addon_short_name)
    @must_have_permission(permissions.WRITE)
    def _set_config(node_addon, user_addon, auth, **kwargs):
        """View for changing a node's linked folder."""
        folder = request.json.get('selected')
        set_folder(node_addon, folder, auth)

        path = folder['path']
        return {
            'result': {
                'folder': {
                    'name': path.replace('All Files', '') if path != 'All Files' else '/ (Full {0})'.format(
                        addon_full_name
                    ),
                    'path': path,
                },
                'urls': Serializer(node_settings=node_addon).addon_serialized_urls,
            },
            'message': 'Successfully updated settings.',
        }
    _set_config.__name__ = '{0}_set_config'.format(addon_short_name)
    return _set_config

def deauthorize_node(addon_short_name):
    @must_not_be_registration
    @must_have_addon(addon_short_name, 'node')
    @must_have_permission(permissions.WRITE)
    def _deauthorize_node(auth, node_addon, **kwargs):
        node_addon.deauthorize(auth=auth)
        node_addon.save()
    _deauthorize_node.__name__ = '{0}_deauthorize_node'.format(addon_short_name)
    return _deauthorize_node
