# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.mendeley.views import mendeley_views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/mendeley/accounts/',
            ],
            'get',
            mendeley_views.account_list(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/settings/',
                '/project/<pid>/node/<nid>/mendeley/settings/',
            ],
            'get',
            mendeley_views.get_config(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/settings/',
                '/project/<pid>/node/<nid>/mendeley/settings/',
            ],
            'put',
            mendeley_views.set_config(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/user_auth/',
                '/project/<pid>/node/<nid>/mendeley/user_auth/',
            ],
            'put',
            mendeley_views.import_auth(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/user_auth/',
                '/project/<pid>/node/<nid>/mendeley/user_auth/',
            ],
            'delete',
            mendeley_views.deauthorize_node(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/widget/',
                '/project/<pid>/node/<nid>/mendeley/widget/',
            ],
            'get',
            mendeley_views.widget(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/citations/',
                '/project/<pid>/node/<nid>/mendeley/citations/',
                '/project/<pid>/mendeley/citations/<list_id>/',
                '/project/<pid>/node/<nid>/mendeley/citations/<list_id>/',
            ],
            'get',
            mendeley_views.citation_list(),
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}
