"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/link/settings/',
            '/project/<pid>/node/<nid>/link/settings/',
        ], 'post', views.link_set_config, json_renderer),
        Rule([
            '/project/<pid>/link/widget/',
            '/project/<pid>/node/<nid>/link/widget/',
        ], 'get', views.link_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/link/',
            '/project/<pid>/node/<nid>/link/',
        ], 'get', views.link_page, OsfWebRenderer('../addons/link/templates/link_page.mako')),
    ],
}
