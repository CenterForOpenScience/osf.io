from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [
        # Settings
        Rule([
            '/settings/twofactor/',
        ], 'put', views.twofactor_settings_put, json_renderer),
        Rule([
            '/settings/twofactor/',
        ], 'get', views.twofactor_settings_get, json_renderer),

        # Enable Two-factor
        Rule([
            '/settings/twofactor/',
        ], 'post', views.enable_twofactor, json_renderer),
        # Disable Two-factor
        Rule([
            '/settings/twofactor/',
        ], 'delete', views.disable_twofactor, json_renderer),

    ],
    'prefix': '/api/v1'
}
