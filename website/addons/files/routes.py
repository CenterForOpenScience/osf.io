"""

"""

from framework.routing import Rule, json_renderer

from .views import files_disable

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/files/disable/',
            '/project/<pid>/node/<nid>/settings/files/disable/',
        ], 'post', files_disable   , json_renderer),
    ],
    'prefix': '/api/v1',
}
