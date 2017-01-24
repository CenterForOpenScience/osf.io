# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.zotero.views import zotero_views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/zotero/accounts/',
            ],
            'get',
            zotero_views.account_list(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/settings/',
                '/project/<pid>/node/<nid>/zotero/settings/',
            ],
            'get',
            zotero_views.get_config(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/settings/',
                '/project/<pid>/node/<nid>/zotero/settings/',
            ],
            'put',
            zotero_views.set_config(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/user_auth/',
                '/project/<pid>/node/<nid>/zotero/user_auth/',
            ],
            'put',
            zotero_views.import_auth(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/user_auth/',
                '/project/<pid>/node/<nid>/zotero/user_auth/',
            ],
            'delete',
            zotero_views.deauthorize_node(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/widget/',
                '/project/<pid>/node/<nid>/zotero/widget/',
            ],
            'get',
            zotero_views.widget(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/citations/',
                '/project/<pid>/node/<nid>/zotero/citations/',
                '/project/<pid>/zotero/citations/<list_id>/',
                '/project/<pid>/node/<nid>/zotero/citations/<list_id>/',
            ],
            'get',
            zotero_views.citation_list(),
            json_renderer,
        ),

    ],
    'prefix': '/api/v1',

}
