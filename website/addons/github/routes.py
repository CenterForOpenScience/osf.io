# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.github import views


api_routes = {
    'rules': [

        Rule(
            [
                '/project/<pid>/github/repos/',
                '/project/<pid>/node/<nid>/github/repos/',
            ],

            'post',
            views.repos.github_create_repo,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/hgrid/root/',
                '/project/<pid>/node/<nid>/github/hgrid/root/',
            ],
            'get',
            views.hgrid.github_root_folder_public,
            json_renderer,
        ),
        Rule(
            [
                '/settings/github/accounts/',
            ],
            'get',
            views.config.github_get_user_accounts,
            json_renderer,

        ),
        # Configuration
        Rule(
            [
                '/project/<pid>/github/settings/',
                '/project/<pid>/node/<nid>/github/settings/',
            ],
            'post',
            views.config.github_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/settings/',
                '/project/<pid>/node/<nid>/github/settings/',
            ],
            'get',
            views.config.github_get_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/repos/',
                '/project/<pid>/node/<nid>/github/repos/',
            ],
            'get',
            views.config.github_repo_list,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/tar/',
                '/project/<pid>/node/<nid>/github/tar/',
            ],
            'get',
            views.crud.github_download_starball,
            json_renderer,
            {'archive': 'tar'},
            endpoint_suffix='__tar',
        ),
        Rule(
            [
                '/project/<pid>/github/zip/',
                '/project/<pid>/node/<nid>/github/zip/',
            ],
            'get',
            views.crud.github_download_starball,
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
            views.hooks.github_hook_callback,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/authorizations/',
                '/project/<pid>/node/<nid>/github/authorizations/',
            ],
            'put',
            views.auth.github_add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/authorizations/',
                '/project/<pid>/node/<nid>/github/authorizations/',
            ],
            'delete',
            views.auth.github_remove_user_auth,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}
