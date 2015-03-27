from framework.routing import Rule, json_renderer

from website.addons.s3 import views


settings_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/s3/newbucket/',
                '/project/<pid>/node/<nid>/s3/newbucket/',
            ],
            'post',
            views.crud.create_new_bucket,
            json_renderer
        ),
        Rule(
            '/settings/s3/',
            'post',
            views.config.s3_authorize_user,
            json_renderer
        ),
        Rule(
            '/settings/s3/',
            'delete',
            views.config.s3_remove_user_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/settings/',
                '/project/<pid>/node/<nid>/s3/settings/',
            ],
            'post',
            views.config.s3_node_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/settings/',
                '/project/<pid>/node/<nid>/s3/settings/',
            ],
            'get',
            views.config.s3_get_node_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/settings/',
                '/project/<pid>/node/<nid>/s3/settings/',
                '/project/<pid>/s3/config/',
                '/project/<pid>/node/<nid>/s3/config/',
            ],
            'delete',
            views.config.s3_remove_node_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/import-auth/',
                '/project/<pid>/node/<nid>/s3/import-auth/',
            ],
            'post',
            views.config.s3_node_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/authorize/',
                '/project/<pid>/node/<nid>/s3/authorize/',
            ],
            'post',
            views.config.s3_authorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/s3/buckets/',
                '/project/<pid>/node/<nid>/s3/buckets/',
            ],
            'get',
            views.config.s3_bucket_list,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}
