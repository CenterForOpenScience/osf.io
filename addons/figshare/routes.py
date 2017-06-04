# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer

from addons.figshare import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/figshare/accounts/',
            ],
            'get',
            views.figshare_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/figshare/settings/',
                '/project/<pid>/node/<nid>/figshare/settings/'
            ],
            'get',
            views.figshare_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/figshare/settings/',
                '/project/<pid>/node/<nid>/figshare/settings/'
            ],
            'put',
            views.figshare_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/figshare/user_auth/',
                '/project/<pid>/node/<nid>/figshare/user_auth/'
            ],
            'put',
            views.figshare_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/figshare/user_auth/',
                '/project/<pid>/node/<nid>/figshare/user_auth/'
            ],
            'delete',
            views.figshare_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/figshare/folders/',
                '/project/<pid>/node/<nid>/figshare/folders/',
            ],
            'get',
            views.figshare_folder_list,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
