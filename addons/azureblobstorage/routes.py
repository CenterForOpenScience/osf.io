from framework.routing import Rule, json_renderer

from addons.azureblobstorage import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/azureblobstorage/accounts/',
            ],
            'post',
            views.azureblobstorage_add_user_account,
            json_renderer,
        ),
        Rule(
            [
                '/settings/azureblobstorage/accounts/',
            ],
            'get',
            views.azureblobstorage_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/azureblobstorage/settings/',
                '/project/<pid>/node/<nid>/azureblobstorage/settings/',
            ],
            'put',
            views.azureblobstorage_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/azureblobstorage/settings/',
                '/project/<pid>/node/<nid>/azureblobstorage/settings/',
            ],
            'get',
            views.azureblobstorage_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/azureblobstorage/user-auth/',
                '/project/<pid>/node/<nid>/azureblobstorage/user-auth/',
            ],
            'put',
            views.azureblobstorage_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/azureblobstorage/user-auth/',
                '/project/<pid>/node/<nid>/azureblobstorage/user-auth/',
            ],
            'delete',
            views.azureblobstorage_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/azureblobstorage/buckets/',
                '/project/<pid>/node/<nid>/azureblobstorage/buckets/',
            ],
            'get',
            views.azureblobstorage_folder_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/azureblobstorage/newcontainer/',
                '/project/<pid>/node/<nid>/azureblobstorage/newcontainer/',
            ],
            'post',
            views.azureblobstorage_create_container,
            json_renderer
        ),
    ],
    'prefix': '/api/v1',
}
