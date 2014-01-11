"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [

        # Configuration
        Rule([
            '/project/<pid>/github/settings/',
            '/project/<pid>/node/<nid>/github/settings/',
        ], 'post', views.github_set_config, json_renderer),

        Rule([
            '/project/<pid>/github/widget/',
            '/project/<pid>/node/<nid>/github/widget/',
        ], 'get', views.github_widget, json_renderer),
        Rule([
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'get', views.github_download_file, json_renderer),
        Rule([
            '/project/<pid>/github/',
            '/project/<pid>/node/<nid>/github/',
        ], 'get', views.github_get_repo, json_renderer),
        Rule([
            '/project/<pid>/github/file/',
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'post', views.github_upload_file, json_renderer),
        Rule([
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'delete', views.github_delete_file, json_renderer),
        Rule([
            '/project/<pid>/github/tarball/',
            '/project/<pid>/node/<nid>/github/tarball/',
        ], 'get', views.github_download_starball, json_renderer, {'archive': 'tar'}, endpoint_suffix='__tar'),
        Rule([
            '/project/<pid>/github/zipball/',
            '/project/<pid>/node/<nid>/github/zipball/',
        ], 'get', views.github_download_starball, json_renderer, {'archive': 'zip'}, endpoint_suffix='__zip'),

        Rule([
            '/project/<pid>/github/hook/',
            '/project/<pid>/node/<nid>github/hook/',
        ], 'post', views.github_hook_callback, json_renderer),

        # OAuth: User
        Rule(
            '/settings/github/oauth/',
            'get', views.github_oauth_start, json_renderer,
            endpoint_suffix='__user'),
        Rule(
            '/settings/github/oauth/delete/', 'post',
            views.github_oauth_delete_user, json_renderer,
        ),

        # OAuth: Node
        Rule([
            '/project/<pid>/github/oauth/',
            '/project/<pid>/node/<nid>/github/oauth/',
        ], 'get', views.github_oauth_start, json_renderer),
        Rule([
            '/project/<pid>/github/user_auth/',
            '/project/<pid>/node/<nid>/github/user_auth/',
        ], 'post', views.github_add_user_auth, json_renderer),
        Rule([
            '/project/<pid>/github/oauth/delete/',
            '/project/<pid>/node/<nid>/github/oauth/delete/',
        ], 'post', views.github_oauth_delete_node, json_renderer),

        # OAuth: General
        Rule([
            '/addons/github/callback/<uid>/',
            '/addons/github/callback/<uid>/<nid>/',
        ], 'get', views.github_oauth_callback, json_renderer),

    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/github/',
            '/project/<pid>/node/<nid>/github/',
        ], 'get', views.github_page, OsfWebRenderer('../addons/github/templates/github_page.mako')),
        Rule([
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'get', views.github_view_file, OsfWebRenderer('../addons/github/templates/github_file.mako')),
    ],
}
