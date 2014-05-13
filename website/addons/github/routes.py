"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

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
            views.config.github_set_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/file/',
                '/project/<pid>/github/file/<path:path>',
                '/project/<pid>/node/<nid>/github/file/',
                '/project/<pid>/node/<nid>/github/file/<path:path>',
            ],
            'post',
            views.crud.github_upload_file,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/file/<path:path>',
                '/project/<pid>/node/<nid>/github/file/<path:path>',
            ],
            'delete',
            views.crud.github_delete_file,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/tarball/',
                '/project/<pid>/node/<nid>/github/tarball/',
            ],
            'get',
            views.crud.github_download_starball,
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

        # OAuth: User
        Rule(
            '/settings/github/oauth/',
            'get',
            views.auth.github_oauth_start,
            json_renderer,
            endpoint_suffix='__user',
        ),
        Rule(
            '/settings/github/oauth/',
            'delete',
            views.auth.github_oauth_delete_user,
            json_renderer,
        ),

        # OAuth: Node
        Rule(
            [
                '/project/<pid>/github/oauth/',
                '/project/<pid>/node/<nid>/github/oauth/',
            ],
            'get',
            views.auth.github_oauth_start,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/user_auth/',
                '/project/<pid>/node/<nid>/github/user_auth/',
            ],
            'post',
            views.auth.github_add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/github/oauth/',
                '/project/<pid>/node/<nid>/github/oauth/',
            ],
            'delete',
            views.auth.github_oauth_delete_node,
            json_renderer,
        ),

        # OAuth: General
        Rule(
            [
                '/addons/github/callback/<uid>/',
                '/addons/github/callback/<uid>/<nid>/',
            ],
            'get',
            views.auth.github_oauth_callback,
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
            views.repos.github_create_repo,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/github/hgrid/',
                '/project/<pid>/node/<nid>/github/hgrid/',
                '/project/<pid>/github/hgrid/<path:path>/',
                '/project/<pid>/node/<nid>/github/hgrid/<path:path>/',
            ],
            'get',
            views.hgrid.github_hgrid_data_contents,
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

        ### File Render ###
        Rule(
            [
                '/project/<pid>/github/file/<path:path>/render/',
                '/project/<pid>/node/<nid>/github/file/<path:path>/render/',
            ],
            'get',
            views.crud.github_get_rendered_file,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}

page_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/github/file/<path:path>/',
                '/project/<pid>/node/<nid>/github/file/<path:path>/',
            ],
            'get',
            views.crud.github_view_file,
            OsfWebRenderer('../addons/github/templates/github_view_file.mako'),
        ),
        Rule(
            [
                '/project/<pid>/github/file/<path:path>/download/',
                '/project/<pid>/node/<nid>/github/file/<path:path>/download/',
            ],
            'get',
            views.crud.github_download_file,
            json_renderer,
        ),
    ],
}
