"""
Routes associated with the jupyterhub addon
"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

TEMPLATE_DIR = './addons/jupyterhub/templates/'

settings_routes = {
    'rules': [],
    'prefix': '/api/v1',
}

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/jupyterhub/widget/',
            '/project/<pid>/node/<nid>/jupyterhub/widget/',
        ], 'get', views.jupyterhub_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

api_routes = {
    'rules': [
        Rule([
            '/project/<pid>/jupyterhub/settings',
            '/project/<pid>/node/<nid>/jupyterhub/settings',
        ], 'get', views.jupyterhub_get_config, json_renderer),
        Rule([
            '/project/<pid>/jupyterhub/settings',
            '/project/<pid>/node/<nid>/jupyterhub/settings',
        ], 'put', views.jupyterhub_set_config, json_renderer),
        Rule([
            '/project/<pid>/jupyterhub/services',
            '/project/<pid>/node/<nid>/jupyterhub/services',
        ], 'get', views.jupyterhub_get_services, json_renderer),
    ],
    'prefix': '/api/v1',
}
