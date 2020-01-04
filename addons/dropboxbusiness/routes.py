# -*- coding: utf-8 -*-
"""Dropbox Business addon routes."""
from framework.routing import Rule, json_renderer

from addons.dropboxbusiness import views


auth_routes = {
    'rules': [
    ],
    'prefix': '/api/v1'
}

api_routes = {
    'rules': [

        ##### Webhook #####
        Rule(
            ['/addons/dropboxbusiness/webhook/'],
            'get',
            views.webhook_challenge,
            json_renderer
        ),
        Rule(
            ['/addons/dropboxbusiness/webhook/'],
            'post',
            views.webhook_post,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
