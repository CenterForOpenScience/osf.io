# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.github import views

settings_routes = {
    'rules': [

        # Configuration
        Rule(
            [
                '/project/<pid>/github/settings/',
                '/project/<pid>/node/<nid>/github/settings/',
            ],
            'post',
            views.github_set_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/tarball/',
                '/project/<pid>/node/<nid>/github/tarball/',
            ],
            'get',
            views.github_download_starball,
            json_renderer,
            {'archive': 'tar'},
            endpoint_suffix='__tar',
        ),
        Rule(
            [
                '/project/<pid>/github/zipball/',
                '/project/<pid>/node/<nid>/github/zipball/',
            ],
            'get',
            views.github_download_starball,
            json_renderer,
            {'archive': 'zip'},
            endpoint_suffix='__zip',
        ),

        Rule(
            [
                '/project/<pid>/github/hook/',
                '/project/<pid>/node/<nid>/github/hook/',
            ],
            'post',
            views.github_hook_callback,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}

api_routes = {
    'rules': [

        Rule(
            '/github/repo/create/',
            'post',
            views.github_create_repo,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/hgrid/root/',
                '/project/<pid>/node/<nid>/github/hgrid/root/',
            ],
            'get',
            views.github_root_folder,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}
