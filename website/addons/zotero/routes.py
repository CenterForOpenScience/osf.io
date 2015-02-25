# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.zotero import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/zotero/accounts/',
            ],
            'get',
            views.list_zotero_accounts_user,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/settings/',
                '/project/<pid>/node/<nid>/zotero/settings/',
            ],
            'get',
            views.zotero_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/settings/',
                '/project/<pid>/node/<nid>/zotero/settings/',
            ],
            'put',
            views.zotero_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/user_auth/',
                '/project/<pid>/node/<nid>/zotero/user_auth/',
            ],
            'post',
            views.zotero_add_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/user_auth/',
                '/project/<pid>/node/<nid>/zotero/user_auth/',
            ],
            'delete',
            views.zotero_remove_user_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/widget/',
                '/project/<pid>/node/<nid>/zotero/widget/',
            ],
            'get',
            views.zotero_widget,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/zotero/citations/',
                '/project/<pid>/node/<nid>/zotero/citations/',
                '/project/<pid>/zotero/citations/<zotero_list_id>/',
                '/project/<pid>/node/<nid>/zotero/citations/<zotero_list_id>/',
            ],
            'get',
            views.zotero_citation_list,
            json_renderer,

        ),

    ],
    'prefix': '/api/v1',

}
