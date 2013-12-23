"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from .views import (github_settings, github_disable, github_page,
                    github_download_file, github_download_tarball)

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/github/',
            '/project/<pid>/node/<nid>/settings/github/',
        ], 'post', github_settings, json_renderer),
        Rule([
            '/project/<pid>/settings/github/disable/',
            '/project/<pid>/node/<nid>/settings/github/disable/',
        ], 'post', github_disable   , json_renderer),
        Rule([
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'get', github_download_file, json_renderer),
        Rule([
            '/project/<pid>/github/tarball/',
            '/project/<pid>/node/<nid>/github/tarball',
        ], 'get', github_download_tarball, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/github/',
            '/project/<pid>/node/<nid>/github/',
        ], 'get', github_page, OsfWebRenderer('project/addon.mako')),
    ],
}
