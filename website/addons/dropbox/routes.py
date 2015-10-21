# -*- coding: utf-8 -*-
"""Dropbox addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.dropbox import views


auth_routes = {
    'rules': [

        Rule(
            '/settings/dropbox/accounts/',
            'get',
            views.auth.dropbox_user_config_get,
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
            views.config.dropbox_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/config/',
            '/project/<pid>/node/<nid>/dropbox/config/'],
            'put',
            views.config.dropbox_config_put,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/dropbox/config/',
            '/project/<pid>/node/<nid>/dropbox/config/'],
            'delete',
            views.config.dropbox_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/config/import-auth/',
            '/project/<pid>/node/<nid>/dropbox/config/import-auth/'],
            'put',
            views.config.dropbox_import_user_auth,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/config/share/',
            '/project/<pid>/node/<nid>/dropbox/config/share/'],
            'get',
            views.config.dropbox_get_share_emails,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/dropbox/folders/',
            '/project/<pid>/node/<nid>/dropbox/folders/'],
            'get',
            views.config.dropbox_get_folders,
            json_renderer
        ),

        ##### HGrid #####
        Rule(
            [
                '/project/<pid>/dropbox/hgrid/',
                '/project/<pid>/node/<nid>/dropbox/hgrid/',
                '/project/<pid>/dropbox/hgrid/<path:path>',
                '/project/<pid>/node/<nid>/dropbox/hgrid/<path:path>',
            ],
            'get',
            views.hgrid.dropbox_hgrid_data_contents,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
