# -*- coding: utf-8 -*-

from website.addons.base.exceptions import AddonError
from dropbox.client import DropboxClient


def get_client(user):
    """Return a :class:`dropbox.client.DropboxClient`, using a user's
    access token.

    :param User user: The user.
    :raises: AddonError if user does not have the Dropbox addon enabled.
    """
    user_settings = user.get_addon('dropbox')
    if not user_settings:
        raise AddonError('User does not have the Dropbox addon enabled.')
    return DropboxClient(user_settings.access_token)


def get_client_from_user_settings(settings_obj):
    """Same as get client, except its argument is a DropboxUserSettingsObject."""
    return get_client(settings_obj.owner)


def get_node_client(node):
    node_settings = node.get_addon('dropbox')
    return get_node_addon_client(node_settings)


def get_node_addon_client(node_addon):
    if node_addon:
        if node_addon.has_auth:
            return get_client_from_user_settings(node_addon.user_settings)
        else:
            raise AddonError('Node is not authorized')
    raise AddonError('Node does not have the Dropbox addon enabled.')
