"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging

from framework import request
from website.project.decorators import (must_have_addon,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)

from website.addons.dropbox.client import get_client


logger = logging.getLogger(__name__)
debug = logger.debug

@must_be_valid_project
@must_have_addon('dropbox', 'node')
def dropbox_config_get(**kwargs):
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']
    client = get_client(node_settings.user_settings.owner)
    # TODO(sloria): Handle error
    metadata = client.metadata('/')
    folders = [each['path'] for each in metadata['contents']]
    return {
        'result': {
            'folders': folders,
            'ownerName': node_settings.user_settings.account_info['display_name'],
            'urls': {
                'config': node.api_url_for('dropbox_config_put')
            }
        },
        'status': 200
    }, 200


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_config_put(**kwargs):
    node_settings = kwargs['node_addon']
    folder = request.json.get('selected')
    node_settings.folder = folder
    node_settings.save()
    return {
        'result': {
            'folder': folder
        },
        'message': 'Successfully updated settings.',
        'status': 200
    }
