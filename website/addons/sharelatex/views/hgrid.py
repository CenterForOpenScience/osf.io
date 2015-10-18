# -*- coding: utf-8 -*-

from website.util import rubeus


def sharelatex_hgrid_data(node_settings, auth, **kwargs):
    # Dont display if not properly configured
    if not node_settings.complete:
        return

    node = node_settings.owner
    return [
        rubeus.build_addon_root(
            node_settings, node_settings.project, permissions=auth,
            nodeUrl=node.url, nodeApiUrl=node.api_url,
        )
    ]
