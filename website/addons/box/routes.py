# -*- coding: utf-8 -*-
"""Box addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.box import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/box/accounts/',
            ],
            'get',
            views.box_get_user_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/box/settings/',
                '/project/<pid>/node/<nid>/box/settings/'
            ],
            'get',
            views.box_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/box/settings/',
                '/project/<pid>/node/<nid>/box/settings/'
            ],
            'put',
            views.box_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/box/user_auth/',
                '/project/<pid>/node/<nid>/box/user_auth/'
            ],
            'put',
            views.box_add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/box/user_auth/',
                '/project/<pid>/node/<nid>/box/user_auth/'
            ],
            'delete',
            views.box_remove_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/box/config/share/',
                '/project/<pid>/node/<nid>/box/config/share/'
            ],
            'get',
            views.box_get_share_emails,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/box/folders/',
                '/project/<pid>/node/<nid>/box/folders/',
            ],
            'get',
            views.box_folder_list,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
