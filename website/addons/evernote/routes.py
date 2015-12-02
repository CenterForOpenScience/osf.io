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
            views.evernote_get_user_settings,
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

        Rule(
            [
                '/project/<pid>/evernote/settings/',
                '/project/<pid>/node/<nid>/evernote/settings/'
            ],
            'put',
            views.evernote_set_config,
            json_renderer,
        ),


        Rule(
            [
                '/project/<pid>/evernote/user_auth/',
                '/project/<pid>/node/<nid>/evernote/user_auth/'
            ],
            'put',
            views.evernote_add_user_auth,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/evernote/folders/',
                '/project/<pid>/node/<nid>/evernote/folders/',
            ],
            'get',
            views.evernote_folder_list,
            json_renderer,
        ),


    ],
    'prefix': '/api/v1',
}
