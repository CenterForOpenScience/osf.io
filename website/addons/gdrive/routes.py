# -*- coding: utf-8 -*-
"""Routes for the gdrive addon.
"""

from framework.routing import Rule, json_renderer

from . import views

# Routes that use the web renderer
web_routes = {
    'rules': [

    ],
}

# JSON endpoints
api_routes = {
    'rules': [


        #### Profile settings ###
        Rule(
            ['/settings/gdrive'],
            'get',
            views.config.drive_user_config_get,
            json_renderer,

        ),


        Rule(
            ['/settings/gdrive/oauth'],
            'delete',
            views.auth.drive_oauth_delete_user,
            json_renderer,
        ),

        Rule(
            ['/settings/gdrive/oauth/'],
            'post',
            views.auth.drive_oauth_start,
            json_renderer,
            endpoint_suffix='_user'
        ),

        Rule(
            ['/addons/gdrive/callback/'],
            'get',
            views.auth.drive_oauth_finish,
            json_renderer,
        ),


        ##### Node settings #####

        Rule(
            ['/project/<pid>/gdrive/oauth/',
             '/project/<pid>/node/<nid>/gdrive/oauth/'],
            'post',
            views.auth.drive_oauth_start,
            json_renderer,
        ),

        Rule(
            ['/project/<pid>/gdrive/get-children/',
             '/project/<pid>/node/<nid>/gdrive/get-children/'],
            'get',
            views.hgrid.gdrive_folders,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/',
             '/project/<pid>/node/<nid>/gdrive/config/'],
            'get',
            views.config.gdrive_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/',
             '/project/<pid>/node/<nid>/gdrive/config/'],
            'put',
            views.config.gdrive_config_put,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/',
             '/project/<pid>/node/<nid>/gdrive/config/'],
            'delete',
            views.auth.gdrive_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/import-auth/',
             '/project/<pid>/node/<nid>/gdrive/config/import-auth/'],
            'put',
            views.auth.gdrive_import_user_auth,
            json_renderer
        ),
    ],

    ## Your routes here

    'prefix': '/api/v1'
}
