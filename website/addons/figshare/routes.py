"""

"""

from framework.routing import Rule, json_renderer

from .views import figshare_settings, figshare_disable

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/figshare/',
            '/project/<pid>/node/<nid>/settings/figshare/',
        ], 'post', figshare_settings, json_renderer),
        Rule([
            '/project/<pid>/settings/figshare/disable/',
            '/project/<pid>/node/<nid>/settings/figshare/disable/',
        ], 'post', figshare_disable, json_renderer),
    ],
    'prefix': '/api/v1',
}
