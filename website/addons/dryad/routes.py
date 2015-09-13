# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.dryad import views

settings_routes = {
    'rules': [

        # Configuration
        Rule(
            [
                '/project/<pid>/dryad/settings/',
                '/project/<pid>/node/<nid>/dryad/settings/',
            ],
            'post',
            views.config.dryad_set_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dryad/tarball/',
                '/project/<pid>/node/<nid>/dryad/tarball/',
            ],
            'get',
            views.crud.dryad_download_starball,
            json_renderer,
            {'archive': 'tar'},
            endpoint_suffix='__tar',
        ),
        Rule(
            [
                '/project/<pid>/dryad/zipball/',
                '/project/<pid>/node/<nid>/dryad/zipball/',
            ],
            'get',
            views.crud.dryad_download_starball,
            json_renderer,
            {'archive': 'zip'},
            endpoint_suffix='__zip',
        ),

        Rule(
            [
                '/project/<pid>/dryad/hook/',
                '/project/<pid>/node/<nid>/dryad/hook/',
            ],
            'post',
            views.hooks.dryad_hook_callback,
            json_renderer,
        ),

        # OAuth: User
        Rule(
            '/settings/dryad/oauth/',
            'get',
            views.auth.dryad_oauth_start,
            json_renderer,
            endpoint_suffix='__user',
        ),
        Rule(
            '/settings/dryad/oauth/',
            'delete',
            views.auth.dryad_oauth_delete_user,
            json_renderer,
        ),

        # OAuth: Node
        Rule(
            [
                '/project/<pid>/dryad/oauth/',
                '/project/<pid>/node/<nid>/dryad/oauth/',
            ],
            'get',
            views.auth.dryad_oauth_start,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/user_auth/',
                '/project/<pid>/node/<nid>/dryad/user_auth/',
            ],
            'post',
            views.auth.dryad_add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/oauth/',
                '/project/<pid>/node/<nid>/dryad/oauth/',
                '/project/<pid>/dryad/config/',
                '/project/<pid>/node/<nid>/dryad/config/'

            ],
            'delete',
            views.auth.dryad_oauth_deauthorize_node,
            json_renderer,
        ),

        # OAuth: General
        Rule(
            [
                '/addons/dryad/callback/<uid>/',
                '/addons/dryad/callback/<uid>/<nid>/',
            ],
            'get',
            views.auth.dryad_oauth_callback,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}

api_routes = {
    'rules': [

        Rule(
            '/dryad/repo/create/',
            'post',
            views.repos.dryad_create_repo,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dryad/hgrid/root/',
                '/project/<pid>/node/<nid>/dryad/hgrid/root/',
            ],
            'get',
            views.hgrid.dryad_root_folder_public,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}
