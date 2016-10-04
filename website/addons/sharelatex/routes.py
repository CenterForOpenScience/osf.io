from framework.routing import Rule, json_renderer

from website.addons.sharelatex import views


settings_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/sharelatex/newproject/',
                '/project/<pid>/node/<nid>/sharelatex/newproject/',
            ],
            'post',
            views.crud.sharelatex_new_project,
            json_renderer
        ),
        Rule(
            '/settings/sharelatex/',
            'post',
            views.config.sharelatex_post_user_settings,
            json_renderer
        ),
        Rule(
            '/settings/sharelatex/',
            'delete',
            views.config.sharelatex_delete_user_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/sharelatex/settings/',
                '/project/<pid>/node/<nid>/sharelatex/settings/',
            ],
            'post',
            views.config.sharelatex_post_node_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/sharelatex/settings/',
                '/project/<pid>/node/<nid>/sharelatex/settings/',
            ],
            'get',
            views.config.sharelatex_get_node_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/sharelatex/settings/',
                '/project/<pid>/node/<nid>/sharelatex/settings/',
                '/project/<pid>/sharelatex/config/',
                '/project/<pid>/node/<nid>/sharelatex/config/',
            ],
            'delete',
            views.config.sharelatex_delete_node_settings,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/sharelatex/import-auth/',
                '/project/<pid>/node/<nid>/sharelatex/import-auth/',
            ],
            'post',
            views.config.sharelatex_node_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/sharelatex/authorize/',
                '/project/<pid>/node/<nid>/sharelatex/authorize/',
            ],
            'post',
            views.config.sharelatex_authorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/sharelatex/project/',
                '/project/<pid>/node/<nid>/sharelatex/project/',
            ],
            'get',
            views.config.sharelatex_get_project_list,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}
