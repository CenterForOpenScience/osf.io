# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer

from . import views

# JSON endpoints
api_routes = {
    'rules': [
        Rule(
            '/settings/owncloud/',
            'get',
            views.owncloud_user_config_get,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/owncloud/user-auth/',
                '/project/<pid>/node/<nid>/owncloud/user-auth/',
            ],
            'delete',
            views.owncloud_deauthorize_node,
            json_renderer,
        ),
        Rule(
            '/settings/owncloud/accounts/',
            'get',
            views.owncloud_account_list,
            json_renderer,
        ),
        Rule(
            ['/project/<pid>/owncloud/settings/',
             '/project/<pid>/node/<nid>/owncloud/settings/'],
            'get',
            views.owncloud_get_config,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/owncloud/settings/',
             '/project/<pid>/node/<nid>/owncloud/settings/'],
            'put',
            views.owncloud_set_config,
            json_renderer
        ),
        Rule(
            ['/settings/owncloud/accounts/'],
            'post',
            views.owncloud_add_user_account,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/owncloud/user-auth/',
                '/project/<pid>/node/<nid>/owncloud/user-auth/',
            ],
            'put',
            views.owncloud_import_auth,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/owncloud/folders/',
             '/project/<pid>/node/<nid>/owncloud/folders/'],
            'get',
            views.owncloud_folder_list,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
