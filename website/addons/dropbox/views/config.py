"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging

from framework import request
from framework.auth import get_current_user
from website.project.decorators import (must_have_addon,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)
from website.util import api_url_for

from website.addons.dropbox.client import get_client


logger = logging.getLogger(__name__)
debug = logger.debug


@must_be_valid_project
@must_have_addon('dropbox', 'node')
def dropbox_config_get(**kwargs):
    user = get_current_user()
    user_settings = user.get_addon('dropbox')
    user_has_auth = user_settings is not None and user_settings.has_auth
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']
    urls = {
        'config': node.api_url_for('dropbox_config_put'),
        'deauthorize': node.api_url_for('dropbox_deauthorize'),
        'auth': api_url_for('dropbox_oauth_start', pid=kwargs['pid'],
            nid=kwargs.get('nid'))
    }
    if node_settings.has_auth:
        client = get_client(node_settings.user_settings.owner)
        # TODO: handle error
        metadata = client.metadata('/', list=True)
        # List each folder, including the root
        folders = ['/'] + [each['path'] for each in metadata['contents'] if each['is_dir']]
        result = {
            'folders': folders,
            'folder': node_settings.folder if node_settings.folder else '/',
            'ownerName': node_settings.user_settings.account_info['display_name'],
            'urls': urls,
            'nodeHasAuth': node_settings.has_auth,
            'userHasAuth': user_has_auth
        }
    else:
        result = {
            'nodeHasAuth': node_settings.has_auth,
            'userHasAuth': user_has_auth,
            'urls': urls
        }
    return {
        'result': result,
        'status': 200
    }, 200


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_config_put(node_addon, **kwargs):
    folder = request.json.get('selected')
    node_addon.folder = folder
    node_addon.save()
    return {
        'result': {
            'folder': folder
        },
        'message': 'Successfully updated settings.',
        'status': 200
    }


@must_have_permission('write')
@must_have_addon('dropbox', 'node')
def dropbox_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()
    node = node_addon.owner
    return {}
