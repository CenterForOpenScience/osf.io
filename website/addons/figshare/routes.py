"""

"""

from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/figshare/',
            '/project/<pid>/node/<nid>/settings/figshare/',
        ], 'post', views.figshare_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}
