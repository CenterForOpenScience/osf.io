# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer
from website.routes import notemplate
from . import SHORT_NAME
from . import views
from . import oauth

# HTML endpoints
page_routes = {
    'rules': [
        # Home (Base) | GET
        Rule(
            [
                '/<pid>/{}'.format(SHORT_NAME),
                '/<pid>/node/<nid>/{}'.format(SHORT_NAME),
            ],
            'get',
            views.project_binderhub,
            notemplate
        ),
        # OAuth2 URL
        Rule([
            '/project/<pid>/{}/<serviceid>/authorize'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/<serviceid>/authorize'.format(SHORT_NAME),
            '/<pid>/{}/<serviceid>/authorize'.format(SHORT_NAME),
            '/<pid>/node/<nid>/{}/<serviceid>/authorize'.format(SHORT_NAME),
        ], 'get', oauth.binderhub_oauth_authorize, json_renderer),
        Rule([
            '/project/{}/callback'.format(SHORT_NAME),
            '/{}/callback'.format(SHORT_NAME),
        ], 'get', oauth.binderhub_oauth_callback, json_renderer),
    ]
}

# JSON endpoints
api_routes = {
    'rules': [
        Rule([
            '/settings/{}/settings'.format(SHORT_NAME),
        ], 'get', views.binderhub_get_user_config, json_renderer),
        Rule([
            '/settings/{}/settings'.format(SHORT_NAME),
        ], 'put', views.binderhub_set_user_config, json_renderer),
        Rule([
            '/settings/{}/settings'.format(SHORT_NAME),
        ], 'post', views.binderhub_add_user_config, json_renderer),
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'get', views.binderhub_get_config, json_renderer),
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'put', views.binderhub_set_config, json_renderer),
        Rule([
            '/project/<pid>/{}/config'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/config'.format(SHORT_NAME),
        ], 'get', views.binderhub_get_config_ember, json_renderer),
        Rule([
            '/project/<pid>/{}/session'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/session'.format(SHORT_NAME),
        ], 'delete', views.binderhub_logout, json_renderer),
    ],
    'prefix': '/api/v1',
}
