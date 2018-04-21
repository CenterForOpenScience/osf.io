# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer

from addons.nextcloud import views

# JSON endpoints
api_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/nextcloud/user-auth/',
                '/project/<pid>/node/<nid>/nextcloud/user-auth/',
            ],
            'delete',
            views.nextcloud_deauthorize_node,
            json_renderer,
        ),
        Rule(
            '/settings/nextcloud/accounts/',
            'get',
            views.nextcloud_account_list,
            json_renderer,
        ),
        Rule(
            ['/project/<pid>/nextcloud/settings/',
             '/project/<pid>/node/<nid>/nextcloud/settings/'],
            'put',
            views.nextcloud_set_config,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/nextcloud/settings/',
             '/project/<pid>/node/<nid>/nextcloud/settings/'],
            'get',
            views.nextcloud_get_config,
            json_renderer
        ),
        Rule(
            ['/settings/nextcloud/accounts/'],
            'post',
            views.nextcloud_add_user_account,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/nextcloud/user-auth/',
                '/project/<pid>/node/<nid>/nextcloud/user-auth/',
            ],
            'put',
            views.nextcloud_import_auth,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/nextcloud/folders/',
             '/project/<pid>/node/<nid>/nextcloud/folders/'],
            'get',
            views.nextcloud_folder_list,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
