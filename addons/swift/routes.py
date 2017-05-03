from framework.routing import Rule, json_renderer

from addons.swift import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/swift/accounts/',
            ],
            'post',
            views.swift_add_user_account,
            json_renderer,
        ),
        Rule(
            [
                '/settings/swift/accounts/',
            ],
            'get',
            views.swift_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/swift/settings/',
                '/project/<pid>/node/<nid>/swift/settings/',
            ],
            'put',
            views.swift_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/swift/settings/',
                '/project/<pid>/node/<nid>/swift/settings/',
            ],
            'get',
            views.swift_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/swift/user-auth/',
                '/project/<pid>/node/<nid>/swift/user-auth/',
            ],
            'put',
            views.swift_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/swift/user-auth/',
                '/project/<pid>/node/<nid>/swift/user-auth/',
            ],
            'delete',
            views.swift_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/swift/containers/',
                '/project/<pid>/node/<nid>/swift/containers/',
            ],
            'get',
            views.swift_folder_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/swift/newcontainer/',
                '/project/<pid>/node/<nid>/swift/newcontainer/',
            ],
            'post',
            views.swift_create_container,
            json_renderer
        ),
    ],
    'prefix': '/api/v1',
}
