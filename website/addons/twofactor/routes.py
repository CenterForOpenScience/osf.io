from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [
        # Settings
        Rule([
            '/settings/twofactor/',
        ], 'put', views.user_settings_put, json_renderer),
        Rule([
            '/settings/twofactor/',
        ], 'get', views.user_settings_get, json_renderer),

        # Enable Two-factor
        Rule([
            '/settings/twofactor/enable/',
        ], 'post', views.enable_twofactor, json_renderer),
    ],
    'prefix': '/api/v1'
}
