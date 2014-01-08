"""

"""

from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [],
    'prefix': '/api/v1',
}

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/files/widget/',
            '/project/<pid>/node/<nid>/files/widget/',
        ], 'get', views.files_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}