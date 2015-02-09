from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [

        # OAuth: General
        Rule([
            '/settings/twofactor/',
        ], 'post', views.user_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}
