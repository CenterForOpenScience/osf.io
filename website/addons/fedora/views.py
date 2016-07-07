"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging

import httplib as http
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError
from website.addons.fedora.serializer import FedoraSerializer
from website.addons.base import generic_views

logger = logging.getLogger(__name__)
debug = logger.debug

SHORT_NAME = 'fedora'
FULL_NAME = 'Fedora'

fedora_account_list = generic_views.account_list(
    SHORT_NAME,
    FedoraSerializer
)

fedora_import_auth = generic_views.import_auth(
    SHORT_NAME,
    FedoraSerializer
)

def _get_folders(node_addon, folder_id):
    node = node_addon.owner
    return [{
        'id': '/',
        'path': '/',
        'addon': 'fedora',
        'kind': 'folder',
        'name': '/ (Full Fedora)',
        'urls': {
            'folders': node.api_url_for('fedora_folder_list', folderId='/'),
        }
    }]


fedora_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

fedora_get_config = generic_views.get_config(
    SHORT_NAME,
    FedoraSerializer
)

def _set_folder(node_addon, folder, auth):
    uid = folder['id']
    node_addon.set_folder(uid, auth=auth)
    node_addon.save()

fedora_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    FedoraSerializer,
    _set_folder
)

fedora_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

fedora_root_folder = generic_views.root_folder(
    SHORT_NAME
)
