# -*- coding: utf-8 -*-
"""Dropbox addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.dropbox import views
from website.routes import OsfWebRenderer, notemplate


auth_routes = {
    'rules': [

        # OAuth: User
        Rule(
            '/settings/dropbox/oauth/',
            'get',
            views.auth.dropbox_oauth_start,
            json_renderer,
            endpoint_suffix='__user'
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
    # TODO(sloria): Remove this prefix for oauth routes? Not sure.
    'prefix': '/api/v1'
}

web_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/dropbox/files/<path:path>',
                '/project/<pid>/node/<nid>/dropbox/files/<path:path>',
            ],
            'get',
            views.crud.dropbox_view_file,
            OsfWebRenderer('../addons/dropbox/templates/dropbox_view_file.mako'),
        ),
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
