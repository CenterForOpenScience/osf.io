__author__ = 'sunnyharris'
from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer, notemplate

from website.addons.zotero import views

api_routes = {
    'rules': [
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
            views.list_citationlists_node,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}