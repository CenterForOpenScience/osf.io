# -*- coding: utf-8 -*-

from flask import request
from framework.exceptions import HTTPError
from website.util import rubeus
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_addon_authorizer


def dryad_addon_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only."""
    # Quit if node settings does not have authentication
    node = node_settings.owner
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder_name,
        permissions={'edit':True, 'view':True},#auth
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    return [root]
