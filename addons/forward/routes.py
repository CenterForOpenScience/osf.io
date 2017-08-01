# -*- coding: utf-8 -*-
"""Forward addon routes."""
from framework.routing import Rule, json_renderer
from addons.forward import views

api_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/forward/config/',
                '/project/<pid>/node/<nid>/forward/config/'
            ],
            'get',
            views.config.forward_config_get,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/forward/config/',
                '/project/<pid>/node/<nid>/forward/config/'
            ],
            'put',
            views.config.forward_config_put,
            json_renderer,
        ),

    ],

    'prefix': '/api/v1',

}
