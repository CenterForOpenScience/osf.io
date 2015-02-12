"""

"""

from framework.routing import Rule, json_renderer

from . import views

settings_routes = {
    'rules': [
        # OAuth: Node
        Rule([
            '/project/<pid>/figshare/oauth/',
            '/project/<pid>/node/<nid>/figshare/oauth',
        ], 'get', views.auth.figshare_oauth_start, json_renderer),
        Rule([
            '/project/<pid>/figshare/user_auth/',
            '/project/<pid>/node/<nid>/figshare/user_auth/',
        ], 'post', views.auth.figshare_add_user_auth, json_renderer),
        Rule([
            '/project/<pid>/figshare/oauth/',
            '/project/<pid>/node/<nid>/figshare/oauth/',
        ], 'delete', views.auth.figshare_oauth_delete_node, json_renderer),
        # OAuth: User
        Rule(
            '/settings/figshare/oauth/',
            'get', views.auth.figshare_oauth_start, json_renderer,
            endpoint_suffix='__user'
        ),
        Rule(
            '/settings/figshare/oauth/',
            'delete', views.auth.figshare_oauth_delete_user, json_renderer
        ),
        # OAuth: General
        Rule([
            '/addons/figshare/callback/<uid>/',
            '/addons/figshare/callback/<uid>/<nid>/',
        ], 'get', views.auth.figshare_oauth_callback, json_renderer),
        Rule([
            '/project/<pid>/figshare/new/project/',
            '/project/<pid>/node/<nid>/figshare/new/project/',
        ], 'post', views.crud.figshare_create_project, json_renderer),
        Rule([
            '/project/<pid>/figshare/new/fileset/',
            '/project/<pid>/node/<nid>/figshare/new/fileset/',
        ], 'post', views.crud.figshare_create_fileset, json_renderer)
    ],
    'prefix': '/api/v1',
}

api_routes = {
    'rules': [
        ##### Node settings #####
        Rule(
            ['/project/<pid>/figshare/config/',
            '/project/<pid>/node/<nid>/figshare/config/'],
            'get',
            views.config.figshare_config_get,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/figshare/config/',
            '/project/<pid>/node/<nid>/figshare/config/'],
            'put',
            views.config.figshare_config_put,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/figshare/hgrid/options/',
            '/project/<pid>/node/<nid>/figshare/hgrid/options/'],
            'get',
            views.config.figshare_get_options,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/figshare/config/import-auth/',
            '/project/<pid>/node/<nid>/figshare/config/import-auth/'],
            'put',
            views.config.figshare_import_user_auth,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/figshare/config/',
            '/project/<pid>/node/<nid>/figshare/config/'],
            'delete',
            views.config.figshare_deauthorize,
            json_renderer
        ),

        #######################
        Rule([
            '/project/<pid>/figshare/hgrid/',
            '/project/<pid>/node/<nid>/figshare/hgrid/',
            '/project/<pid>/figshare/hgrid/<type>/<id>/',
            '/project/<pid>/node/<nid>/figshare/hgrid/<type>/<id>/',

        ], 'get', views.hgrid.figshare_hgrid_data_contents, json_renderer),
    ],
    'prefix': '/api/v1',
}
