# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer
from website.addons.evernote import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/evernote/accounts/',
            ],
            'get',
            views.evernote_get_user_accounts,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/evernote/settings/',
                '/project/<pid>/node/<nid>/evernote/settings/'
            ],
            'get',
            views.evernote_get_config,
            json_renderer,
        ),
        
    ],
    'prefix': '/api/v1',
}
