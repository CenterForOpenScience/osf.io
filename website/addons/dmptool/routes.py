# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer
from website.addons.dmptool import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/dmptool/accounts/',
            ],
            'get',
            views.dmptool_get_user_settings,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dmptool/settings/',
                '/project/<pid>/node/<nid>/dmptool/settings/'
            ],
            'get',
            views.dmptool_get_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dmptool/settings/',
                '/project/<pid>/node/<nid>/dmptool/settings/'
            ],
            'put',
            views.dmptool_set_config,
            json_renderer,
        ),


        Rule(
            [
                '/project/<pid>/dmptool/user_auth/',
                '/project/<pid>/node/<nid>/dmptool/user_auth/'
            ],
            'put',
            views.dmptool_add_user_auth,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dmptool/user_auth/',
                '/project/<pid>/node/<nid>/dmptool/user_auth/'
            ],
            'delete',
            views.dmptool_deauthorize_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/dmptool/widget/',
                '/project/<pid>/node/<nid>/dmptool/widget/',
            ],
            'get',
            views.dmptool_widget,
            json_renderer,
        ),



    ],
    'prefix': '/api/v1',
}
