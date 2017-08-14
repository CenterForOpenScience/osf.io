# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from addons.bitbucket import views

api_routes = {
    'rules': [

        Rule(
            [
                '/settings/bitbucket/accounts/',
            ],
            'get',
            views.bitbucket_account_list,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/bitbucket/settings/',
                '/project/<pid>/node/<nid>/bitbucket/settings/'
            ],
            'get',
            views.bitbucket_get_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/bitbucket/settings/',
                '/project/<pid>/node/<nid>/bitbucket/settings/',
            ],
            'post',
            views.bitbucket_set_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/bitbucket/user_auth/',
                '/project/<pid>/node/<nid>/bitbucket/user_auth/'
            ],
            'put',
            views.bitbucket_import_auth,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/bitbucket/user_auth/',
                '/project/<pid>/node/<nid>/bitbucket/user_auth/'
            ],
            'delete',
            views.bitbucket_deauthorize_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/bitbucket/tarball/',
                '/project/<pid>/node/<nid>/bitbucket/tarball/',
            ],
            'get',
            views.bitbucket_download_starball,
            json_renderer,
            {'archive': 'tar'},
            endpoint_suffix='__tar',
        ),
        Rule(
            [
                '/project/<pid>/bitbucket/zipball/',
                '/project/<pid>/node/<nid>/bitbucket/zipball/',
            ],
            'get',
            views.bitbucket_download_starball,
            json_renderer,
            {'archive': 'zip'},
            endpoint_suffix='__zip',
        ),

        Rule(
            [
                '/project/<pid>/bitbucket/hgrid/root/',
                '/project/<pid>/node/<nid>/bitbucket/hgrid/root/',
            ],
            'get',
            views.bitbucket_root_folder,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}
