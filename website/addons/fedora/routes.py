# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer

from website.addons.fedora import views

# JSON endpoints
api_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/fedora/user-auth/',
                '/project/<pid>/node/<nid>/fedora/user-auth/',
            ],
            'delete',
            views.fedora_deauthorize_node,
            json_renderer,
        ),
        Rule(
            '/settings/fedora/accounts/',
            'get',
            views.fedora_account_list,
            json_renderer,
        ),
        Rule(
            ['/project/<pid>/fedora/settings/',
             '/project/<pid>/node/<nid>/fedora/settings/'],
            'put',
            views.fedora_set_config,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/fedora/settings/',
             '/project/<pid>/node/<nid>/fedora/settings/'],
            'get',
            views.fedora_get_config,
            json_renderer
        ),
        Rule(
            ['/settings/fedora/accounts/'],
            'post',
            views.fedora_add_user_account,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/fedora/user-auth/',
                '/project/<pid>/node/<nid>/fedora/user-auth/',
            ],
            'put',
            views.fedora_import_auth,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/fedora/folders/',
             '/project/<pid>/node/<nid>/fedora/folders/'],
            'get',
            views.fedora_folder_list,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
