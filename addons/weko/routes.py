from framework.routing import Rule, json_renderer, xml_renderer
from website.routes import OsfWebRenderer

from . import views

oauth_routes = {
    'rules': [
        Rule(
            '/connect/weko/<repoid>/',
            'get',
            views.weko_oauth_connect,
            json_renderer,
        ),
        Rule(
            '/callback/weko/<repoid>/',
            'get',
            views.weko_oauth_callback,
            OsfWebRenderer('util/oauth_complete.mako', trust=False),
        ),
    ],
    'prefix': '/oauth'
  }

api_routes = {
    'rules': [
        Rule(
            '/settings/weko/',
            'get',
            views.weko_user_config_get,
            json_renderer,
        ),
        Rule(
            '/settings/weko/accounts/',
            'get',
            views.weko_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/settings/',
                '/project/<pid>/node/<nid>/weko/settings/',
            ],
            'get',
            views.weko_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/settings/',
                '/project/<pid>/node/<nid>/weko/settings/',
            ],
            'put',
            views.weko_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/serviceitemtype/',
                '/project/<pid>/node/<nid>/weko/serviceitemtype/',
            ],
            'get',
            views.weko_get_serviceitemtype,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/user-auth/',
                '/project/<pid>/node/<nid>/weko/user-auth/',
            ],
            'put',
            views.weko_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/user-auth/',
                '/project/<pid>/node/<nid>/weko/user-auth/',
            ],
            'delete',
            views.weko_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/hgrid/root/',
                '/project/<pid>/node/<nid>/weko/hgrid/root/',
            ],
            'get',
            views.weko_root_folder,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/item_view/<itemid>/',
                '/project/<pid>/node/<nid>/weko/item_view/<itemid>/',
            ],
            'get',
            views.weko_get_item_view,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/indices/',
                '/project/<pid>/node/<nid>/weko/indices/',
            ],
            'post',
            views.weko_create_index,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/item_log/',
                '/project/<pid>/node/<nid>/weko/item_log/',
            ],
            'post',
            views.weko_add_item_created,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/metadata/',
                '/project/<pid>/node/<nid>/weko/metadata/',
            ],
            'get',
            views.weko_generate_metadata,
            xml_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
