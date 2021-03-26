# -*- coding: utf-8 -*-
"""Routes for the googledriveinstitutions addon.
"""

from framework.routing import Rule, json_renderer

from . import views

# JSON endpoints
api_routes = {
    'rules': [

        #### Profile settings ###

        Rule(
            [
                '/settings/googledriveinstitutions/accounts/',
            ],
            'get',
            views.googledriveinstitutions_account_list,
            json_renderer,

        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/googledriveinstitutions/folders/',
             '/project/<pid>/node/<nid>/googledriveinstitutions/folders/'],
            'get',
            views.googledriveinstitutions_folder_list,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledriveinstitutions/config/',
             '/project/<pid>/node/<nid>/googledriveinstitutions/config/'],
            'get',
            views.googledriveinstitutions_get_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledriveinstitutions/config/',
             '/project/<pid>/node/<nid>/googledriveinstitutions/config/'],
            'put',
            views.googledriveinstitutions_set_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledriveinstitutions/config/',
             '/project/<pid>/node/<nid>/googledriveinstitutions/config/'],
            'delete',
            views.googledriveinstitutions_deauthorize_node,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledriveinstitutions/config/import-auth/',
             '/project/<pid>/node/<nid>/googledriveinstitutions/config/import-auth/'],
            'put',
            views.googledriveinstitutions_import_auth,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
