from addons.boa import views
from framework.routing import Rule, json_renderer

api_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/boa/user-auth/',
                '/project/<pid>/node/<nid>/boa/user-auth/',
            ],
            'delete',
            views.boa_deauthorize_node,
            json_renderer,
        ),
        Rule(
            '/settings/boa/accounts/',
            'get',
            views.boa_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/boa/settings/',
                '/project/<pid>/node/<nid>/boa/settings/'
            ],
            'get',
            views.boa_get_config,
            json_renderer
        ),
        Rule(
            [
                '/settings/boa/accounts/'
            ],
            'post',
            views.boa_add_user_account,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/boa/user-auth/',
                '/project/<pid>/node/<nid>/boa/user-auth/',
            ],
            'put',
            views.boa_import_auth,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/boa/submit-job/',
                '/project/<pid>/node/<nid>/boa/submit-job/',
            ],
            'post',
            views.boa_submit_job,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
