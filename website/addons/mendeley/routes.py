# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.mendeley import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/mendeley/accounts/',
            ],
            'get',
            views.list_accounts_user,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/settings/',
                '/project/<pid>/node/<nid>/mendeley/settings/',
            ],
            'get',
            views.get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/settings/',
                '/project/<pid>/node/<nid>/mendeley/settings/',
            ],
            'put',
            views.set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/user_auth/',
                '/project/<pid>/node/<nid>/mendeley/user_auth/',
            ],
            'post',
            views.add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/user_auth/',
                '/project/<pid>/node/<nid>/mendeley/user_auth/',
            ],
            'delete',
            views.remove_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/widget/',
                '/project/<pid>/node/<nid>/mendeley/widget/',
            ],
            'get',
            views.mendeley_widget,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/mendeley/citations/',
                '/project/<pid>/node/<nid>/mendeley/citations/',
                '/project/<pid>/mendeley/citations/<mendeley_list_id>/',
                '/project/<pid>/node/<nid>/mendeley/citations/<mendeley_list_id>/',
            ],
            'get',
            views.citation_list,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}
