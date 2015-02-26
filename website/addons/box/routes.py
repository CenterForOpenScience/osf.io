# -*- coding: utf-8 -*-
"""Box addon routes."""
from framework.routing import Rule, json_renderer

from website.addons.box import views


auth_routes = {
    'rules': [

        ##### OAuth #####

        Rule(
            '/oauth/connect/box/',
            'get',
            views.auth.box_oauth_start,  # Use same view func as node oauth start
            json_renderer,
            endpoint_suffix='_user'          # but add a suffix for url_for
        ),

        Rule(
            '/oauth/callback/box/',
            'get',
            views.auth.box_oauth_finish,
            json_renderer,
        ),

        Rule(
            '/oauth/accounts/box/',
            'delete',
            views.auth.box_oauth_delete_user,
            json_renderer,
        ),
    ],
}


api_routes = {
    'rules': [

        ##### OAuth #####

        # avoid nginx rewrite (lack of 307 support)
        Rule(
            [
                '/project/<pid>/oauth/connect/box/',
                '/project/<pid>/node/<nid>/oauth/connect/box/',
            ],
            'get',
            views.auth.box_oauth_start,
            json_renderer,
        ),

        #### Profile settings ###

        Rule(
            '/settings/box/',
            'get',
            views.auth.box_user_config_get,
            json_renderer,
        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/box/config/',
            '/project/<pid>/node/<nid>/box/config/'],
            'get',
            views.config.box_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/box/config/',
            '/project/<pid>/node/<nid>/box/config/'],
            'put',
            views.config.box_config_put,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/box/config/',
            '/project/<pid>/node/<nid>/box/config/'],
            'delete',
            views.config.box_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/box/config/import-auth/',
            '/project/<pid>/node/<nid>/box/config/import-auth/'],
            'put',
            views.config.box_import_user_auth,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/box/config/share/',
            '/project/<pid>/node/<nid>/box/config/share/'],
            'get',
            views.config.box_get_share_emails,
            json_renderer
        ),

        ##### HGrid #####
        Rule(
            [
                '/project/<pid>/box/hgrid/',
                '/project/<pid>/node/<nid>/box/hgrid/',
                '/project/<pid>/box/hgrid/<path:path>',
                '/project/<pid>/node/<nid>/box/hgrid/<path:path>',
            ],
            'get',
            views.hgrid.box_hgrid_data_contents,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
