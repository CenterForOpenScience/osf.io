from framework.routing import Rule, json_renderer

from website.addons.s3 import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/s3/accounts/',
            ],
            'post',
            views.s3_add_user_account,
            json_renderer,
        ),
        Rule(
            [
                '/settings/s3/accounts/',
            ],
            'get',
            views.s3_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/settings/',
                '/project/<pid>/node/<nid>/s3/settings/',
            ],
            'put',
            views.s3_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/settings/',
                '/project/<pid>/node/<nid>/s3/settings/',
            ],
            'get',
            views.s3_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/user-auth/',
                '/project/<pid>/node/<nid>/s3/user-auth/',
            ],
            'put',
            views.s3_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/user-auth/',
                '/project/<pid>/node/<nid>/s3/user-auth/',
            ],
            'delete',
            views.s3_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/buckets/',
                '/project/<pid>/node/<nid>/s3/buckets/',
            ],
            'get',
            views.s3_folder_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/newbucket/',
                '/project/<pid>/node/<nid>/s3/newbucket/',
            ],
            'post',
            views.create_bucket,
            json_renderer
        ),
    ],
    'prefix': '/api/v1',
}
