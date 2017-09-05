# -*- coding: utf-8 -*-
"""OneDrive addon routes."""
from framework.routing import Rule, json_renderer

from addons.onedrive import views


api_routes = {
    'rules': [
        #### Profile settings ###
        Rule(
            [
                '/settings/onedrive/accounts/',
            ],
            'get',
            views.onedrive_account_list,
            json_renderer,
        ),
        ##### Node settings #####
        Rule(
            [
                '/project/<pid>/onedrive/folders/',
                '/project/<pid>/node/<nid>/onedrive/folders/',
            ],
            'get',
            views.onedrive_folder_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/config/',
                '/project/<pid>/node/<nid>/onedrive/config/'
            ],
            'get',
            views.onedrive_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/config/',
                '/project/<pid>/node/<nid>/onedrive/config/'
            ],
            'put',
            views.onedrive_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/config/',
                '/project/<pid>/node/<nid>/onedrive/config/'
            ],
            'delete',
            views.onedrive_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/onedrive/import-auth/',
                '/project/<pid>/node/<nid>/onedrive/import-auth/'
            ],
            'put',
            views.onedrive_import_auth,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
