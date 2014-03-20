from website.routes import OsfWebRenderer
from framework.routing import Rule, json_renderer

from . import views


widget_route = {
    'rules': [
        Rule([
            '/project/<pid>/badges/widget/',
            '/project/<pid>/node/<nid>/badges/widget/',
        ], 'get', views.badges_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

api_urls = {
    'rules': [
        Rule(
            '/badges/new/',
        'post', views.new_badge, json_renderer),
    ],
    'prefix': '/api/v1',
}

guid_urls = {
    'rules': [
        Rule([
            '/badge/<bid>/',
        ], 'get', views.get_badge, OsfWebRenderer('../addons/badges/templates/view_badge.mako')),
        Rule([
            '/badge/<bid>/json/',
        ], 'get', views.get_badge, json_renderer),
    ]
}
