# -*- coding: utf-8 -*-
"""Dropbox addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.dropbox import views

from . import views

settings_routes = {
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
        )

    ],
    # TODO(sloria): Remove this prefix for oauth routes? Not sure.
    'prefix': '/api/v1'
}

crud_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/dropbox/<path:path>/',
                '/project/<pid>/node/<nid>/dropbox/<path:path>/',
            ],
            'delete',
            views.crud.dropbox_delete_file,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/dropbox/<path:path>/',
                '/project/<pid>/node/<nid>/dropbox/<path:path>/',
            ],
            'get',
            views.crud.dropbox_download,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/dropbox/<path:path>/',
                '/project/<pid>/node/<nid>/dropbox/<path:path>/',
                '/project/<pid>/dropbox/',
                '/project/<pid>/node/<nid>/dropbox/',
            ],
            'post',
            views.crud.dropbox_upload,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/dropbox/hgrid/',
                '/project/<pid>/node/<nid>/dropbox/hgrid/',
                '/project/<pid>/dropbox/hgrid/<path:path>/',
                '/project/<pid>/node/<nid>/dropbox/hgrid/<path:path>/',
            ],
            'get',
            views.hgrid.dropbox_hgrid_data_contents,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
