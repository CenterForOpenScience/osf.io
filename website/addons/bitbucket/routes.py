"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/bitbucket/',
            '/project/<pid>/node/<nid>/settings/bitbucket/',
        ], 'post', views.bitbucket_settings, json_renderer),
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
        Rule([
            '/project/<pid>/bitbucket/oauth/',
            '/project/<pid>/node/<nid>/bitbucket/oauth/',
        ], 'get', views.bitbucket_oauth_start, json_renderer),
        Rule([
            '/project/<pid>/bitbucket/oauth/delete/',
            '/project/<pid>/node/<nid>/bitbucket/oauth/delete/',
        ], 'post', views.bitbucket_oauth_delete, json_renderer),
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
