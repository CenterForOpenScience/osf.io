# -*- coding: utf-8 -*-
"""Routes for the gdrive addon.
"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

# Routes that use the web renderer
web_routes = {
    'rules': [

        ##### View file #####
    #     Rule(
    #         [
    #             '/project/<pid>/gdrive/files/<path:path>',
    #             '/project/<pid>/node/<nid>/gdrive/files/<path:path>',
    #         ],
    #         'get',
    #         views.crud.gdrive_view_file,
    #         OsfWebRenderer('../addons/gdrive/templates/gdrive_view_file.mako'),
    #     ),


    #     ##### Download file #####
    #     Rule(
    #         [
    #             '/project/<pid>/gdrive/files/<path:path>/download/',
    #             '/project/<pid>/node/<nid>/gdrive/files/<path:path>/download/',
    #         ],
    #         'get',
    #         views.crud.gdrive_download,
    #         notemplate,
    #     ),
    ],
}

# JSON endpoints
api_routes = {
    'rules': [


        #### Profile settings ###
        Rule(
            ['/settings/gdrive'],
             'get',
             views.drive_user_config_get,
             json_renderer,

        ),


        Rule(
            ['/settings/gdrive/oauth'],
            'delete',
            views.drive_oauth_delete_user,
            json_renderer,
        ),

        Rule(
            ['/settings/gdrive/oauth/'],
            'post',
            views.drive_oauth_start,
            json_renderer,
            endpoint_suffix='_user'
        ),

        Rule(
            ['/addons/gdrive/callback/'
            ],
            'get',
            views.drive_oauth_finish,
            json_renderer,
        ),


        ##### Node settings #####

         Rule(
            ['/project/<pid>/gdrive/oauth/',
            '/project/<pid>/node/<nid>/gdrive/oauth/',
            ],
            'post',
            views.drive_oauth_start,
            json_renderer,
        ),

        Rule(
            ['/project/<pid>/gdrive/get-children/',
            '/project/<pid>/node/<nid>/gdrive/get-children/'],
            'get',
            views.get_children,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/',
            '/project/<pid>/node/<nid>/gdrive/config/'],
            'get',
            views.gdrive_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/',
            '/project/<pid>/node/<nid>/gdrive/config/'],
            'put',
            views.gdrive_config_put,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/',
            '/project/<pid>/node/<nid>/gdrive/config/'],
            'delete',
            views.gdrive_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/gdrive/config/import-auth/',
            '/project/<pid>/node/<nid>/gdrive/config/import-auth/'],
            'put',
            views.gdrive_import_user_auth,
            json_renderer
        ),
    ],

    ## Your routes here

    'prefix': '/api/v1'
}
