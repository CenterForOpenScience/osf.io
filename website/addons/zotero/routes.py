from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer, notemplate

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
                '/project/<pid>/zotero/accounts/',
                '/project/<pid>/node/<nid>/zotero/accounts/',
            ],
            'get',
            views.list_zotero_accounts_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/zotero/<account_id>/lists/',
                '/project/<pid>/node/<nid>/zotero/<account_id>/lists/',
            ],
            'get',
            views.list_zotero_citationlists_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/zotero/settings/',
                '/project/<pid>/node/<nid>/zotero/settings/',
            ],
            'post',
            views.zotero_set_config,
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
            ],
            'get',
            views.zotero_citation_list,
            json_renderer,

        ),

    ],
    'prefix': '/api/v1'
}