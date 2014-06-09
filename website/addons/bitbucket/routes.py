"""

"""

from framework.routing import Rule, json_renderer
from website.osf_web_renderer import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [

        # Configuration
        Rule([
            '/project/<pid>/bitbucket/settings/',
            '/project/<pid>/node/<nid>/bitbucket/settings/',
        ], 'post', views.bitbucket_set_config, json_renderer),

        Rule([
            '/project/<pid>/bitbucket/file/<path:path>',
            '/project/<pid>/node/<nid>/bitbucket/file/<path:path>',
        ], 'get', views.bitbucket_download_file, json_renderer),
        Rule([
            '/project/<pid>/bitbucket/',
            '/project/<pid>/node/<nid>/bitbucket/',
        ], 'get', views.bitbucket_get_repo, json_renderer),
        Rule([
            '/project/<pid>/bitbucket/tarball/',
            '/project/<pid>/node/<nid>/bitbucket/tarball/',
        ], 'get', views.bitbucket_download_starball, json_renderer, {'archive': 'tar'}, endpoint_suffix='__tar'),
        Rule([
            '/project/<pid>/bitbucket/zipball/',
            '/project/<pid>/node/<nid>/bitbucket/zipball/',
        ], 'get', views.bitbucket_download_starball, json_renderer, {'archive': 'zip'}, endpoint_suffix='__zip'),

        # OAuth: User
        Rule(
            '/settings/bitbucket/oauth/',
            'get', views.bitbucket_oauth_start, json_renderer,
            endpoint_suffix='__user'),
        Rule(
            '/settings/bitbucket/oauth/delete/', 'post',
            views.bitbucket_oauth_delete_user, json_renderer,
        ),

        # OAuth: Node
        Rule([
            '/project/<pid>/bitbucket/oauth/',
            '/project/<pid>/node/<nid>/bitbucket/oauth/',
        ], 'get', views.bitbucket_oauth_start, json_renderer),
        Rule([
            '/project/<pid>/bitbucket/user_auth/',
            '/project/<pid>/node/<nid>/bitbucket/user_auth/',
        ], 'post', views.bitbucket_add_user_auth, json_renderer),
        Rule([
            '/project/<pid>/bitbucket/oauth/delete/',
            '/project/<pid>/node/<nid>/bitbucket/oauth/delete/',
        ], 'post', views.bitbucket_oauth_delete_node, json_renderer),

        # OAuth: General
        Rule([
            '/addons/bitbucket/callback/<uid>/',
            '/addons/bitbucket/callback/<uid>/<nid>/',
        ], 'get', views.bitbucket_oauth_callback, json_renderer),

    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/bitbucket/',
            '/project/<pid>/node/<nid>/bitbucket/',
        ], 'get', views.bitbucket_page, OsfWebRenderer('project/addon/addon.mako')),
    ],
}
