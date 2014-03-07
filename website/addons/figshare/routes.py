"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        #Configuration
        Rule([
            '/project/<pid>/figshare/unlink/',
            '/project/<pid>/node/<nid>/figshare/unlink/'
        ], 'post', views.config.figshare_unlink, json_renderer),
        Rule([
            '/project/<pid>/figshare/settings/',
            '/project/<pid>/node/<nid>/figshare/settings/',
        ], 'post', views.config.figshare_set_config, json_renderer),
        # Widget
        Rule([
            '/project/<pid>/figshare/widget/',
            '/project/<pid>/node/<nid>/figshare/widget/',
        ], 'get', views.widget.figshare_widget, json_renderer),
        # CRUD: Projects
        Rule([
            '/project/<pid>/figshare/project/<project_id>/article',
            '/project/<pid>/node/<nid>/figshare/project/<project_id>/article',
            '/project/<pid>/figshare/project/<project_id>/article/<aid>',
            '/project/<pid>/node/<nid>/figshare/project/<project_id>/article/<aid>'
        ],  'post', views.crud.figshare_add_article_to_project, json_renderer),
        Rule([
            '/project/<pid>/figshare/project/<project_id>/article/<aid>',
            '/project/<pid>/node/<nid>/figshare/project/<project_id>/article/<aid>'
        ],  'delete', views.crud.figshare_remove_article_from_project, json_renderer),
        # CRUD: Articles
        Rule([
            '/project/<pid>/figshare/publish/article/<aid>/',
            '/project/<pid>/node/<nid>/figshare/publish/article/<aid>/'],
             'post', views.crud.figshare_publish_article, json_renderer),
        # CRUD: Files
        Rule([
            '/project/<pid>/figshare/<aid>/',
            '/project/<pid>/node/<nid>/figshare/<aid>/',
        ],  'post', views.crud.figshare_upload_file_to_article, json_renderer),
        Rule([
            '/project/<pid>/figshare/article/<aid>/file/<fid>/',
            '/project/<pid>/node/<nid>/figshare/article/<aid>/file/<fid>/',
        ],  'delete', views.crud.figshare_delete_file, json_renderer),
        Rule([
            '/project/<pid>/figshare/',
            'project/<pid>/node/<nid>/figshare/'
        ], 'post', views.crud.figshare_upload_file_as_article, json_renderer),
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
    ],
    'prefix': '/api/v1',
}

api_routes = {
    'rules': [
        Rule([
            '/project/<pid>/figshare/hgrid/',
            '/project/<pid>/node/<nid>/figshare/hgrid/',
            '/project/<pid>/figshare/hgrid/<type>/<id>',
            '/project/<pid>/node/<nid>/figshare/hgrid/<type>/<id>',

        ], 'get', views.hgrid.figshare_hgrid_data_contents, json_renderer),
        Rule([
            '/project/<pid>/figshare/render/article/<aid>/file/<fid>',
            '/project/<pid>/node/<nid>/figshare/render/article/<aid>/file/<fid>'
        ], 'get', views.crud.figshare_get_rendered_file, json_renderer,),
        Rule([
            '/project/<pid>/figshare/download/article/<aid>/file/<fid>/',
            '/project/<pid>/node/<nid>/figshare/download/article/<aid>/file/<fid>/'
        ], 'get', views.crud.figshare_download_file, json_renderer,),
     ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/figshare/article/<aid>/file/<fid>/',
            '/project/<pid>/node/<nid>/figshare/article/<aid>/file/<fid>/',
        ], 'get', views.crud.figshare_view_file, OsfWebRenderer('../addons/figshare/templates/figshare_view_file.mako')),
    ],
}
