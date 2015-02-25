# -*- coding: utf-8 -*-
from website.util import api_url_for, web_url_for

def serialize_account(account):
    if account is None:
        return None
    return {
        'id': account._id,
        'provider_id': account.provider_id,
        'display_name': account.display_name,
    }

def serialize_folder(name, parent_id=None, list_id=None, id=None):
    retval = {
        'name': name,
        'provider_list_id': list_id,
        'id': id
    }
    if parent_id:
        retval['parent_list_id'] = parent_id

    return retval

def serialize_urls(node_addon):
    """Collects and serializes urls needed for AJAX calls"""

    external_account = node_addon.external_account
    ret = {
        'auth': api_url_for('oauth_connect',
                            service_name=node_addon.provider_name),
        'settings': web_url_for('user_addons'),
        'files': node_addon.owner.url,
    }
    if external_account and external_account.profile_url:
        ret['owner'] = external_account.profile_url

    return ret
