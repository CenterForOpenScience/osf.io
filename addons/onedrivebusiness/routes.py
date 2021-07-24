from addons.onedrivebusiness import SHORT_NAME
from addons.onedrivebusiness import views
from framework.routing import Rule, json_renderer

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/{}/accounts/'.format(SHORT_NAME),
            ],
            'get',
            views.onedrivebusiness_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/{}/settings/'.format(SHORT_NAME),
                '/project/<pid>/node/<nid>/{}/settings/'.format(SHORT_NAME),
            ],
            'get',
            views.onedrivebusiness_get_config,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}
