"""

"""

from framework.routing import Rule, json_renderer

from .views import wiki_disable

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/wiki/disable/',
            '/project/<pid>/node/<nid>/settings/wiki/disable/',
        ], 'post', wiki_disable   , json_renderer),
    ],
    'prefix': '/api/v1',
}
