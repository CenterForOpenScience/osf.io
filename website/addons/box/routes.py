# -*- coding: utf-8 -*-
"""Box addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.box import views
from website.routes import OsfWebRenderer, notemplate


auth_routes = {
    'rules': [

        Rule(
            '/settings/box/',
            'get',
            views.auth.box_user_config_get,
            json_renderer,
        ),

        ##### OAuth #####
        Rule(
            '/settings/box/oauth/',
            'get',
            views.auth.box_oauth_start,  # Use same view func as node oauth start
            json_renderer,
            endpoint_suffix='_user'          # but add a suffix for url_for
        ),

        Rule(
            '/addons/box/oauth/finish/',
            'get',
            views.auth.box_oauth_finish,
            json_renderer,
        ),

        Rule(
            '/settings/box/oauth/',
            'delete',
            views.auth.box_oauth_delete_user,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/box/oauth/',
                '/project/<pid>/node/<nid>/box/oauth/',
            ],
            'get',
            views.auth.box_oauth_start,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}

web_routes = {
    'rules': [

        ##### View file #####
        Rule(
            [
                '/project/<pid>/box/files/<path:path>',
                '/project/<pid>/node/<nid>/box/files/<path:path>',
            ],
            'get',
            views.crud.box_view_file,
            OsfWebRenderer('../addons/box/templates/box_view_file.mako'),
        ),


        ##### Download file #####
        Rule(
            [
                '/project/<pid>/box/files/<path:path>/download/',
                '/project/<pid>/node/<nid>/box/files/<path:path>/download/',
            ],
            'get',
            views.crud.box_download,
            notemplate,
        ),
    ],
}

api_routes = {
    'rules': [

        ##### Node settings #####

        Rule(
            ['/project/<pid>/box/config/',
            '/project/<pid>/node/<nid>/box/config/'],
            'get',
            views.config.box_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/box/config/',
            '/project/<pid>/node/<nid>/box/config/'],
            'put',
            views.config.box_config_put,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/box/config/',
            '/project/<pid>/node/<nid>/box/config/'],
            'delete',
            views.config.box_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/box/config/import-auth/',
            '/project/<pid>/node/<nid>/box/config/import-auth/'],
            'put',
            views.config.box_import_user_auth,
            json_renderer
        ),


        Rule(
            ['/project/<pid>/box/config/share/',
            '/project/<pid>/node/<nid>/box/config/share/'],
            'get',
            views.config.box_get_share_emails,
            json_renderer
        ),

        ##### CRUD #####

        # Delete
        Rule(
            [
                '/project/<pid>/box/files/<path:path>',
                '/project/<pid>/node/<nid>/box/files/<path:path>',
            ],
            'delete',
            views.crud.box_delete_file,
            json_renderer
        ),

        # Upload
        Rule(
            [
                '/project/<pid>/box/files/',
                '/project/<pid>/box/files/<path:path>',
                '/project/<pid>/node/<nid>/box/files/',
                '/project/<pid>/node/<nid>/box/files/<path:path>',
            ],
            'post',
            views.crud.box_upload,
            json_renderer
        ),

        ##### File rendering #####
        Rule(
            [
                '/project/<pid>/box/files/<path:path>/render/',
                '/project/<pid>/node/<nid>/box/files/<path:path>/render/',
            ],
            'get',
            views.crud.box_render_file,
            json_renderer
        ),

        ##### Revisions #####
        Rule(
            [
                '/project/<pid>/box/files/<path:path>/revisions/',
                '/project/<pid>/node/<nid>/box/files/<path:path>/revisions/',
            ],
            'get',
            views.crud.box_get_revisions,
            json_renderer
        ),

        ##### HGrid #####
        Rule(
            [
                '/project/<pid>/box/hgrid/',
                '/project/<pid>/node/<nid>/box/hgrid/',
                '/project/<pid>/box/hgrid/<path:path>',
                '/project/<pid>/node/<nid>/box/hgrid/<path:path>',
            ],
            'get',
            views.hgrid.box_hgrid_data_contents,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
