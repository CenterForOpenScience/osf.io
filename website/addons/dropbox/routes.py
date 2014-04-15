# -*- coding: utf-8 -*-
"""Dropbox addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.dropbox import views
from website.routes import OsfWebRenderer, notemplate


auth_routes = {
    'rules': [

        Rule(
            '/settings/dropbox/',
            'get',
            views.auth.dropbox_user_config_get,
            json_renderer,
        ),

        ##### OAuth #####
        Rule(
            '/settings/dropbox/oauth/',
            'get',
            views.auth.dropbox_oauth_start,  # Use same view func as node oauth start
            json_renderer,
            endpoint_suffix='_user'          # but add a suffix for url_for
        ),

        Rule(
            '/addons/dropbox/oauth/finish/',
            'get',
            views.auth.dropbox_oauth_finish,
            json_renderer,
        ),

        Rule(
            '/settings/dropbox/oauth/',
            'delete',
            views.auth.dropbox_oauth_delete_user,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dropbox/oauth/',
                '/project/<pid>/node/<nid>/dropbox/oauth/',
            ],
            'get',
            views.auth.dropbox_oauth_start,
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
                '/project/<pid>/dropbox/files/<path:path>',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>',
            ],
            'get',
            views.crud.dropbox_view_file,
            OsfWebRenderer('../addons/dropbox/templates/dropbox_view_file.mako'),
        ),


        ##### Download file #####
        Rule(
            [
                '/project/<pid>/dropbox/files/<path:path>/download/',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>/download/',
            ],
            'get',
            views.crud.dropbox_download,
            notemplate,
        ),
    ],
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

        ##### CRUD #####

        # Delete
        Rule(
            [
                '/project/<pid>/dropbox/files/<path:path>',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>',
            ],
            'delete',
            views.crud.dropbox_delete_file,
            json_renderer
        ),

        # Upload
        Rule(
            [
                '/project/<pid>/dropbox/files/',
                '/project/<pid>/dropbox/files/<path:path>',
                '/project/<pid>/node/<nid>/dropbox/files/',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>',
            ],
            'post',
            views.crud.dropbox_upload,
            json_renderer
        ),

        ##### File rendering #####
        Rule(
            [
                '/project/<pid>/dropbox/files/<path:path>/render/',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>/render/',
            ],
            'get',
            views.crud.dropbox_render_file,
            json_renderer
        ),

        ##### Revisions #####
        Rule(
            [
                '/project/<pid>/dropbox/files/<path:path>/revisions/',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>/revisions/',
            ],
            'get',
            views.crud.dropbox_get_revisions,
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
