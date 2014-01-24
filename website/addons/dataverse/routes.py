"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views #todo

settings_routes = {
    'rules': [
        # Project Settings
        Rule([
            '/project/<pid>/dataverse/settings/',
            '/project/<pid>/node/<nid>/dataverse/settings/',
        ], 'post', views.dataverse_set_node_config, json_renderer),

        # User Settings
        Rule(
            '/settings/dataverse/',
            'post',
            views.dataverse_set_user_config,
            json_renderer,
        ),
        Rule(
            '/settings/dataverse/delete',
            'post',
            views.dataverse_delete_user,
            json_renderer,
        ),

        # Widget Settings
        Rule([
            '/project/<pid>/dataverse/widget/',
            '/project/<pid>/node/<nid>/dataverse/widget/',
        ], 'get', views.dataverse_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/dataverse/',
            '/project/<pid>/node/<nid>/dataverse/',
        ], 'get', views.dataverse_page, OsfWebRenderer('../addons/dataverse/templates/dataverse_page.mako')),
    ],
}
