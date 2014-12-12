# -*- coding: utf-8 -*-
"""Utility functions for the Google Drive add-on.
"""
from website.util import web_url_for
import settings
def serialize_urls(node_settings):
    node = node_settings.owner
    urls = {
        'create' : node.api_url_for('drive_oauth_start'),
        'importAuth': node.api_url_for('gdrive_import_user_auth'),
        'deauthorize': node.api_url_for('gdrive_deauthorize'),
        'get_folders' : node.api_url_for('get_children')

    }
    return urls


def serialize_settings(node_settings, current_user):
    """
    View helper that returns a dictionary representation of a GdriveNodeSettings record. Provides the return value for the gdrive config endpoints.
    """
    user_settings = node_settings.user_settings
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )
    current_user_settings = current_user.get_addon('gdrive')
    rv = {
        'nodeHasAuth': node_settings.has_auth,
        'userIsOwner': user_is_owner,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        'api_key' : settings.API_KEY,
        'urls': serialize_urls(node_settings)
    }
    if node_settings.has_auth:
    # Add owner's profile URL
        rv['urls']['owner'] = web_url_for('profile_view_id',
                                               uid=user_settings.owner._primary_key)
        rv['ownerName'] = user_settings.owner.fullname
        rv['access_token'] = user_settings.access_token
    return rv

