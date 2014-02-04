from framework.routing import Rule, json_renderer

from . import views, SHORT_NAME

settings_routes = {
    'rules': [

        # OAuth: General
        Rule([
            '/settings/{}/'.format(SHORT_NAME),
        ], 'post', views.user_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}