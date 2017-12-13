from framework.routing import Rule, json_renderer

from addons.s3compat import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/s3compat/accounts/',
            ],
            'post',
            views.s3compat_add_user_account,
            json_renderer,
        ),
        Rule(
            [
                '/settings/s3compat/accounts/',
            ],
            'get',
            views.s3compat_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3compat/settings/',
                '/project/<pid>/node/<nid>/s3compat/settings/',
            ],
            'put',
            views.s3compat_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3compat/settings/',
                '/project/<pid>/node/<nid>/s3compat/settings/',
            ],
            'get',
            views.s3compat_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3compat/user-auth/',
                '/project/<pid>/node/<nid>/s3compat/user-auth/',
            ],
            'put',
            views.s3compat_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3compat/user-auth/',
                '/project/<pid>/node/<nid>/s3compat/user-auth/',
            ],
            'delete',
            views.s3compat_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3compat/buckets/',
                '/project/<pid>/node/<nid>/s3compat/buckets/',
            ],
            'get',
            views.s3compat_folder_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3compat/newbucket/',
                '/project/<pid>/node/<nid>/s3compat/newbucket/',
            ],
            'post',
            views.s3compat_create_bucket,
            json_renderer
        ),
    ],
    'prefix': '/api/v1',
}
