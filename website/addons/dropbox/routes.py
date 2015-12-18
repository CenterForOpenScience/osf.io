# -*- coding: utf-8 -*-
"""Dropbox addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.dropbox import views


auth_routes = {
    'rules': [

        Rule(
            '/settings/dropbox/accounts/',
            'get',
            views.dropbox_account_list,
            json_renderer,
        )
    ],
    'prefix': '/api/v1'
}

api_routes = {
    'rules': [

        ##### Node settings #####

        Rule(
            ['/project/<pid>/dropbox/config/',
            '/project/<pid>/node/<nid>/dropbox/config/'],
            'get',
            views.dropbox_get_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/config/',
            '/project/<pid>/node/<nid>/dropbox/config/'],
            'put',
            views.dropbox_set_config,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/dropbox/config/',
            '/project/<pid>/node/<nid>/dropbox/config/'],
            'delete',
            views.dropbox_deauthorize_node,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/config/import-auth/',
            '/project/<pid>/node/<nid>/dropbox/config/import-auth/'],
            'put',
            views.dropbox_import_auth,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/folders/',
            '/project/<pid>/node/<nid>/dropbox/folders/'],
            'get',
            views.dropbox_folder_list,
            json_renderer
        ),

    ],
    'prefix': '/api/v1'
}
