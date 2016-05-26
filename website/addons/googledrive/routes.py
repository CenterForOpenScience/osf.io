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
            views.googledrive_account_list,
            json_renderer,

        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/googledrive/folders/',
             '/project/<pid>/node/<nid>/googledrive/folders/'],
            'get',
            views.googledrive_folder_list,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/',
             '/project/<pid>/node/<nid>/googledrive/config/'],
            'get',
            views.googledrive_get_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/',
             '/project/<pid>/node/<nid>/googledrive/config/'],
            'put',
            views.googledrive_set_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/',
             '/project/<pid>/node/<nid>/googledrive/config/'],
            'delete',
            views.googledrive_deauthorize_node,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/import-auth/',
             '/project/<pid>/node/<nid>/googledrive/config/import-auth/'],
            'put',
            views.googledrive_import_auth,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
