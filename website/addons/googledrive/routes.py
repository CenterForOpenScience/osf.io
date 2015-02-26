# -*- coding: utf-8 -*-
"""Routes for the googledrive addon.
"""

from framework.routing import Rule, json_renderer

from . import views

# Routes that use the web renderer
auth_routes = {
    'rules': [

        ##### OAuth #####

        Rule(
            ['/oauth/connect/googledrive/'],
            'post',
            views.auth.googledrive_oauth_start,
            json_renderer,
            endpoint_suffix='_user'
        ),

        Rule(
            ['/oauth/callback/googledrive/'],
            'get',
            views.auth.googledrive_oauth_finish,
            json_renderer,
        ),

        Rule(
            ['/oauth/accounts/googledrive/'],
            'delete',
            views.auth.googledrive_oauth_delete_user,
            json_renderer,
        ),
    ],
}

# JSON endpoints
api_routes = {
    'rules': [

        ##### OAuth #####

        # avoid nginx rewrite (lack of 307 support)
        Rule(
            [
                '/project/<pid>/oauth/connect/googledrive/',
                '/project/<pid>/node/<nid>/oauth/connect/googledrive/'
            ],
            'post',
            views.auth.googledrive_oauth_start,
            json_renderer,
        ),

        #### Profile settings ###

        Rule(
            ['/settings/googledrive'],
            'get',
            views.config.googledrive_user_config_get,
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
