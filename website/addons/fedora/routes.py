# -*- coding: utf-8 -*-
"""Fedora addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.fedora import views


auth_routes = {
    'rules': [

        Rule(
            '/settings/fedora/accounts/',
            'get',
            views.fedora_account_list,
            json_renderer,
        )
    ],
    'prefix': '/api/v1'
}

api_routes = {
    'rules': [

        ##### Node settings #####

        Rule(
            ['/project/<pid>/fedora/config/',
            '/project/<pid>/node/<nid>/fedora/config/'],
            'get',
            views.fedora_get_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/fedora/config/',
            '/project/<pid>/node/<nid>/fedora/config/'],
            'put',
            views.fedora_set_config,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/fedora/config/',
            '/project/<pid>/node/<nid>/fedora/config/'],
            'delete',
            views.fedora_deauthorize_node,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/fedora/config/import-auth/',
            '/project/<pid>/node/<nid>/fedora/config/import-auth/'],
            'put',
            views.fedora_import_auth,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/fedora/folders/',
            '/project/<pid>/node/<nid>/fedora/folders/'],
            'get',
            views.fedora_folder_list,
            json_renderer
        ),

    ],
    'prefix': '/api/v1'
}
