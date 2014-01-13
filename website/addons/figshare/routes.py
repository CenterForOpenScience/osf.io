"""

"""

from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/figshare/settings/',
            '/project/<pid>/node/<nid>/figshare/settings/',
        ], 'post', views.figshare_set_config, json_renderer),
        Rule([
            '/project/<pid>/figshare/widget/',
            '/project/<pid>/node/<nid>/figshare/widget/',
        ], 'get', views.figshare_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}
