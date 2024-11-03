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
        # APIs for user's BinderHub addon settings
        Rule([
            '/settings/{}/settings'.format(SHORT_NAME),
        ], 'get', views.binderhub_get_user_config, json_renderer),
        Rule([
            '/settings/{}/settings'.format(SHORT_NAME),
        ], 'put', views.binderhub_set_user_config, json_renderer),
        Rule([
            '/settings/{}/settings'.format(SHORT_NAME),
        ], 'post', views.binderhub_add_user_config, json_renderer),
        # API to purge a binderhub entry from an user's BinderHub addon setting.
        Rule([
            '/settings/{}/settings/binderhubs'.format(SHORT_NAME),
        ], 'delete', views.purge_binderhub_from_user, json_renderer),
        # APIs for node's BinderHub addon settings
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'get', views.binderhub_get_config, json_renderer),
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'put', views.binderhub_set_config, json_renderer),
        # API to delete binderhub entry from a node.
        Rule([
            '/project/<pid>/{}/settings/binderhubs'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings/binderhubs'.format(SHORT_NAME),
        ], 'delete', views.delete_binderhub, json_renderer),
        # API that reads the config used in RDM-ember-osf-web
        Rule([
            '/project/<pid>/{}/config'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/config'.format(SHORT_NAME),
        ], 'get', views.binderhub_get_config_ember, json_renderer),
        # Server annotations CRUD API.
        Rule([
            '/project/<pid>/{}/server_annotation'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/server_annotation'.format(SHORT_NAME),
        ], 'get', views.get_server_annotation, json_renderer),
        Rule([
            '/project/<pid>/{}/server_annotation'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/server_annotation'.format(SHORT_NAME),
        ], 'post', views.create_server_annotation, json_renderer),
        Rule([
            '/project/<pid>/{}/server_annotation/<aid>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/server_annotation/<aid>'.format(SHORT_NAME),
        ], 'patch', views.patch_server_annotation, json_renderer),
        Rule([
            '/project/<pid>/{}/server_annotation/<aid>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/server_annotation/<aid>'.format(SHORT_NAME),
        ], 'delete', views.delete_server_annotation, json_renderer),
        # API to logout from a BinderHub.
        Rule([
            '/project/<pid>/{}/session'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/session'.format(SHORT_NAME),
        ], 'delete', views.binderhub_logout, json_renderer),
    ],
    'prefix': '/api/v1',
}
