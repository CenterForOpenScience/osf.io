# -*- coding: utf-8 -*-
"""Utility functions for the IQB-RIMS add-on.
"""
import os

from addons.iqbrims.apps import IQBRIMSAddonConfig
from osf.models import ExternalAccount
from website.util import api_v2_url

def build_iqbrims_urls(item, node, path):
    return {
        'fetch': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(node._id), params={'path': path}),
        'folders': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(node._id), params={'path': path, 'id': item['id']})
    }

def to_hgrid(item, node, path):
    """
    :param item: contents returned from IQB-RIMS API
    :return: results formatted as required for Hgrid display
    """
    path = os.path.join(path, item['title'])

    serialized = {
        'path': path,
        'id': item['id'],
        'kind': 'folder',
        'name': item['title'],
        'addon': 'iqbrims',
        'urls': build_iqbrims_urls(item, node, path=path)
    }
    return serialized

def serialize_iqbrims_widget(node):
    iqbrims = node.get_addon('iqbrims')
    ret = {
        'complete': True,
        'include': False,
        'can_expand': True,
    }
    ret.update(iqbrims.config.to_json())
    return ret

def oauth_disconnect_following_other(user, other_user_addon):
    # TODO: fix
    user_addon = user.get_addon(IQBRIMSAddonConfig.short_name)

    for account in user_addon.external_accounts.all():
        exists = other_user_addon.external_accounts.filter(provider_id=account.provider_id).exists()
        if not exists:
            user_addon.revoke_oauth_access(account)
            user_addon.save()
            user.external_accounts.remove(account)
            user.save()

def copy_node_auth(node, other_node_addon):
    node_addon = node.get_or_add_addon(IQBRIMSAddonConfig.short_name)

    # deauthorize node
    if other_node_addon.external_account is None or other_node_addon.user_settings is None:
        node_addon.deauthorize()
        node_addon.save()
        # TODO: oauth_disconnect if other_user_addon
        return

    user = other_node_addon.user_settings.owner
    user_addon = user.get_or_add_addon(IQBRIMSAddonConfig.short_name)

    # copy external_account
    account = create_or_update_external_account_with_other(other_node_addon.external_account)

    # add external_account to user and user_settings if it does not exist
    if not user.external_accounts.filter(id=account.id).exists():
        user.external_accounts.add(account)
        user.save()
    if not user_addon.external_accounts.filter(id=account.id).exists():
        user_addon.external_accounts.add(account)
        user_addon.save()

    # set auth and folder to node_settings
    node_addon.set_auth(account, user)
    node_addon.set_folder({'id': other_node_addon.folder_id, 'path': other_node_addon.folder_path}, auth=None)
    node_addon.save()

def create_or_update_external_account_with_other(other_external_account):
    external_account = ExternalAccount.objects.get(
        provider=IQBRIMSAddonConfig.short_name,
        provider_id=other_external_account.provider_id
    )

    if external_account is None:
        external_account = ExternalAccount(
            scopes=other_external_account.scopes,
            provider_id=other_external_account.provider_id,
            oauth_key=other_external_account.oauth_key,
            provider=IQBRIMSAddonConfig.short_name,
            expires_at=other_external_account.expires_at,
            date_last_refreshed=other_external_account.date_last_refreshed,
            provider_name=IQBRIMSAddonConfig.full_name,
            refresh_token=other_external_account.refresh_token
        )
    else:
        external_account.scopes = other_external_account.scopes
        external_account.oauth_key = other_external_account.oauth_key
        external_account.expires_at = other_external_account.expires_at
        external_account.date_last_refreshed = other_external_account.date_last_refreshed
        external_account.refresh_token = other_external_account.refresh_token

    external_account.save()

    return external_account
