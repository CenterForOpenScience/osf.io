# -*- coding: utf-8 -*-
"""OneDrive addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.onedrive import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/onedrive/accounts/',
            ],
            'get',
            views.onedrive_get_user_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/settings/',
                '/project/<pid>/node/<nid>/onedrive/settings/'
            ],
            'get',
            views.onedrive_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/settings/',
                '/project/<pid>/node/<nid>/onedrive/settings/'
            ],
            'put',
            views.onedrive_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/user_auth/',
                '/project/<pid>/node/<nid>/onedrive/user_auth/'
            ],
            'put',
            views.onedrive_add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/user_auth/',
                '/project/<pid>/node/<nid>/onedrive/user_auth/'
            ],
            'delete',
            views.onedrive_remove_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/config/share/',
                '/project/<pid>/node/<nid>/onedrive/config/share/'
            ],
            'get',
            views.onedrive_get_share_emails,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/folders/',
                '/project/<pid>/node/<nid>/onedrive/folders/',
            ],
            'get',
            views.onedrive_folder_list,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
