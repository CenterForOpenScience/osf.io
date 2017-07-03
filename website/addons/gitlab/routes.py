# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.gitlab import views

api_routes = {
    'rules': [

        Rule(
            '/settings/gitlab/',
            'get',
            views.gitlab_user_config_get,
            json_renderer,
        ),
        Rule(
            '/settings/gitlab/accounts/',
            'post',
            views.gitlab_add_user_account,
            json_renderer,
        ),
        Rule(
            [
                '/settings/gitlab/accounts/',
            ],
            'get',
            views.gitlab_account_list,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/settings/',
                '/project/<pid>/node/<nid>/gitlab/settings/'
            ],
            'get',
            views.gitlab_get_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/settings/',
                '/project/<pid>/node/<nid>/gitlab/settings/',
            ],
            'post',
            views.gitlab_set_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/user_auth/',
                '/project/<pid>/node/<nid>/gitlab/user_auth/'
            ],
            'put',
            views.gitlab_import_auth,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/user_auth/',
                '/project/<pid>/node/<nid>/gitlab/user_auth/'
            ],
            'delete',
            views.gitlab_deauthorize_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/tarball/',
                '/project/<pid>/node/<nid>/gitlab/tarball/',
            ],
            'get',
            views.gitlab_download_starball,
            json_renderer,
            {'archive': 'tar'},
            endpoint_suffix='__tar',
        ),
        Rule(
            [
                '/project/<pid>/gitlab/zipball/',
                '/project/<pid>/node/<nid>/gitlab/zipball/',
            ],
            'get',
            views.gitlab_download_starball,
            json_renderer,
            {'archive': 'zip'},
            endpoint_suffix='__zip',
        ),

        Rule(
            [
                '/project/<pid>/gitlab/hook/',
                '/project/<pid>/node/<nid>/gitlab/hook/',
            ],
            'post',
            views.gitlab_hook_callback,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/repo/create/',
                '/project/<pid>/node/<nid>/gitlab/repo/create/',

            ],
            'post',
            views.gitlab_create_repo,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/hgrid/root/',
                '/project/<pid>/node/<nid>/gitlab/hgrid/root/',
            ],
            'get',
            views.gitlab_root_folder,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}
