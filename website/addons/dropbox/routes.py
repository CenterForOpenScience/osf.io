# -*- coding: utf-8 -*-
"""Dropbox addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.dropbox import views

settings_routes = {
    'rules': [

        # OAuth: User
        Rule(
            '/settings/dropbox/oauth/',
            'get',
            views.auth.dropbox_oauth_start,
            json_renderer,
            endpoint_suffix='__user'
        ),

        Rule(
            '/addons/dropbox/oauth/finish/',
            'get',
            views.auth.dropbox_oauth_finish,
            json_renderer,
        ),

        Rule(
            '/settings/dropbox/oauth/',
            'delete',
            views.auth.dropbox_oauth_delete_user,
            json_renderer,
        )

    ],
    'prefix': '/api/v1/'
}

api_routes = {
    'rules': [
    ],
    'prefix': '/api/v1/'
}

nonapi_routes = {
    'rules': [
    ]
}
