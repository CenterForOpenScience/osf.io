"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/s3/',
            '/project/<pid>/node/<nid>/settings/s3/',
        ], 'post', views.s3_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/s3/',
            '/project/<pid>/node/<nid>/s3/',
        ], 'get', views.s3_page, OsfWebRenderer('../addons/s3/templates/s3_page.mako')),
    ],
}

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/s3/widget/',
            '/project/<pid>/node/<nid>/s3/widget/',
        ], 'get', views.s3_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}