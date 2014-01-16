"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views


settings_routes = {
    'rules': [],
    'prefix': '/api/v1',
}

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/wiki/widget/',
            '/project/<pid>/node/<nid>/wiki/widget/',
        ], 'get', views.wiki_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}
