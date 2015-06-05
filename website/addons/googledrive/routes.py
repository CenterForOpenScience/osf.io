# -*- coding: utf-8 -*-
"""Routes for the googledrive addon.
"""

from framework.routing import Rule, json_renderer

from . import views

# JSON endpoints
api_routes = {
    'rules': [

        #### Profile settings ###

        Rule(
            [
                '/settings/googledrive/accounts/',
            ],
            'get',
            views.config.list_googledrive_user_accounts,
            json_renderer,

        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/googledrive/folders/',
             '/project/<pid>/node/<nid>/googledrive/folders/'],
            'get',
            views.hgrid.googledrive_folders,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/',
             '/project/<pid>/node/<nid>/googledrive/config/'],
            'get',
            views.config.googledrive_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/',
             '/project/<pid>/node/<nid>/googledrive/config/'],
            'put',
            views.config.googledrive_config_put,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/',
             '/project/<pid>/node/<nid>/googledrive/config/'],
            'delete',
            views.config.googledrive_remove_user_auth,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/import-auth/',
             '/project/<pid>/node/<nid>/googledrive/config/import-auth/'],
            'put',
            views.config.googledrive_import_user_auth,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
