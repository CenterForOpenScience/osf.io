from framework.routing import Rule, json_renderer
#from website.routes import OsfWebRenderer

from . import views

api_routes = {
    'rules': [
        Rule(
            '/settings/dmptool/',
            'get',
            views.dmptool_user_config_get,
            json_renderer,
        ),
        Rule(
            '/settings/dmptool/accounts/',
            'post',
            views.dmptool_add_user_account,
            json_renderer,
        ),
        Rule(
            '/settings/dmptool/accounts/',
            'get',
            views.dmptool_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dmptool/settings/',
                '/project/<pid>/node/<nid>/dmptool/settings/',
            ],
            'get',
            views.dmptool_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dmptool/settings/',
                '/project/<pid>/node/<nid>/dmptool/settings/',
            ],
            'post',
            views.dmptool_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dmptool/user-auth/',
                '/project/<pid>/node/<nid>/dmptool/user-auth/',
            ],
            'put',
            views.dmptool_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dmptool/user-auth/',
                '/project/<pid>/node/<nid>/dmptool/user-auth/',
            ],
            'delete',
            views.dmptool_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dmptool/hgrid/root/',
                '/project/<pid>/node/<nid>/dmptool/hgrid/root/',
            ],
            'get',
            views.dmptool_root_folder,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
