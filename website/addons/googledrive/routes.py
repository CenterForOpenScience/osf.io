# -*- coding: utf-8 -*-
"""Routes for the googledrive addon.
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
            ['/settings/googledrive'],
            'get',
            views.config.googledrive_user_config_get,
            json_renderer,

        ),

        Rule(
            ['/settings/googledrive/oauth'],
            'delete',
            views.auth.googledrive_oauth_delete_user,
            json_renderer,
        ),

        Rule(
            ['/settings/googledrive/oauth/'],
            'post',
            views.auth.googledrive_oauth_start,
            json_renderer,
            endpoint_suffix='_user'
        ),

        Rule(
            ['/addons/googledrive/finish/'],
            'get',
            views.auth.googledrive_oauth_finish,
            json_renderer,
        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/googledrive/oauth/',
             '/project/<pid>/node/<nid>/googledrive/oauth/'],
            'post',
            views.auth.googledrive_oauth_start,
            json_renderer,
        ),

        Rule(
            ['/project/<pid>/googledrive/get-children/',
             '/project/<pid>/node/<nid>/googledrive/get-children/'],
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
            views.auth.googledrive_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/googledrive/config/import-auth/',
             '/project/<pid>/node/<nid>/googledrive/config/import-auth/'],
            'put',
            views.auth.googledrive_import_user_auth,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
