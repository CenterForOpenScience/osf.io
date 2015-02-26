# -*- coding: utf-8 -*-
from box import BoxClient

from website.addons.base.exceptions import AddonError


def get_client(user):
    """Return a :class:`boxview.boxview.BoxView`, using a user's
    access token.

    :param User user: The user.
    :raises: AddonError if user does not have the Box addon enabled.
    """
    user_settings = user.get_addon('box')
    if not user_settings:
        raise AddonError('User does not have the Box addon enabled.')
    return get_client_from_user_settings(user_settings)


def get_client_from_user_settings(settings_obj):
    """Same as get client, except its argument is a BoxUserSettingsObject."""
    if settings_obj.has_auth:
        # fetching the access token will guarantee a refresh
        settings_obj.fetch_access_token()
        return BoxClient(settings_obj.get_credentialsv2())
    raise AddonError('Box credentials for this user have expired.')


def get_node_client(node):
    node_settings = node.get_addon('box')
    return get_node_addon_client(node_settings)


def get_node_addon_client(node_addon):
    if node_addon:
        if node_addon.has_auth:
            return get_client_from_user_settings(node_addon.user_settings)
        else:
            raise AddonError('Node is not authorized')
    raise AddonError('Node does not have the Box addon enabled.')
