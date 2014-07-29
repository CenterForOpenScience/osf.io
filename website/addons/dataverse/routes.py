"""

"""

from framework.routing import Rule, json_renderer
from website.addons.dataverse.views.widget import dataverse_get_widget_contents, \
    dataverse_widget
from website.routes import OsfWebRenderer, notemplate

from . import views

settings_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/dataverse/config/',
            '/project/<pid>/node/<nid>/dataverse/config/'],
            'get',
            views.config.dataverse_config_get,
            json_renderer
        ),
        Rule([
            '/project/<pid>/dataverse/set/',
            '/project/<pid>/node/<nid>/dataverse/set/',
        ], 'post', views.config.set_dataverse_and_study, json_renderer),
        Rule([
            '/project/<pid>/dataverse/deauthorize/',
            '/project/<pid>/node/<nid>/dataverse/deauthorize/',
            '/project/<pid>/dataverse/config/',
            '/project/<pid>/node/<nid>/dataverse/config/',
        ], 'delete', views.auth.deauthorize_dataverse, json_renderer),

        # User Settings
        Rule(
            '/settings/dataverse/',
            'get',
            views.auth.dataverse_user_config_get,
            json_renderer,
        ),
        Rule(
            '/settings/dataverse/',
            'post',
            views.config.dataverse_set_user_config,
            json_renderer,
        ),
        Rule(
            '/settings/dataverse/',
            'delete',
            views.auth.dataverse_delete_user,
            json_renderer,
        ),

        # Files
        Rule([
            '/project/<pid>/dataverse/file/',
            '/project/<pid>/dataverse/file/<path:path>/',
            '/project/<pid>/node/<nid>/dataverse/file/',
            '/project/<pid>/node/<nid>/dataverse/file/<path:path>/',
        ], 'post', views.crud.dataverse_upload_file, json_renderer),
        Rule([
            '/project/<pid>/dataverse/file/<path:path>/',
            '/project/<pid>/node/<nid>/dataverse/file/<path:path>/',
        ], 'delete', views.crud.dataverse_delete_file, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/dataverse/file/<path:path>/',
                '/project/<pid>/node/<nid>/dataverse/file/<path:path>/',
            ],
            'get',
            views.crud.dataverse_view_file,
            OsfWebRenderer('../addons/dataverse/templates/dataverse_view_file.mako')
        ),
        Rule(
            [
                '/project/<pid>/dataverse/file/<path:path>/download/',
                '/project/<pid>/node/<nid>/dataverse/file/<path:path>/download/',
            ],
            'get',
            views.crud.dataverse_download_file,
            notemplate,
        ),
    ],
}

api_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/dataverse/config/get-studies/',
            '/project/<pid>/node/<nid>/dataverse/config/get-studies/'],
            'post',
            views.config.dataverse_get_studies,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/dataverse/config/import-auth/',
            '/project/<pid>/node/<nid>/dataverse/config/import-auth/'],
            'put',
            views.config.dataverse_import_user_auth,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/dataverse/hgrid/',
                '/project/<pid>/node/<nid>/dataverse/hgrid/',
                '/project/<pid>/dataverse/hgrid/<path:path>/',
                '/project/<pid>/node/<nid>/dataverse/hgrid/<path:path>/',
            ],
            'get',
            views.hgrid.dataverse_hgrid_data_contents,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/hgrid/root/',
                '/project/<pid>/node/<nid>/dataverse/hgrid/root/',
            ],
            'get',
            views.hgrid.dataverse_root_folder_public,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/file/<path:path>/render/',
                '/project/<pid>/node/<nid>/dataverse/file/<path:path>/render/',
            ],
            'get',
            views.crud.dataverse_get_rendered_file,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/file/<path:path>/proxy/',
                '/project/<pid>/node/<nid>/dataverse/file/<path:path>/proxy/',
            ],
            'get',
            views.crud.dataverse_download_file_proxy,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/release/',
                '/project/<pid>/node/<nid>/dataverse/release/',
            ],
            'put',
            views.crud.dataverse_release_study,
            json_renderer,
        ),
        Rule(
            [
            '/project/<pid>/dataverse/widget/',
            '/project/<pid>/node/<nid>/dataverse/widget/',
            ],
            'get',
            dataverse_widget,
            OsfWebRenderer('../addons/dataverse/templates/dataverse_widget.mako'),
        ),
        Rule(
            [
            '/project/<pid>/dataverse/widget/contents/',
            '/project/<pid>/node/<nid>/dataverse/widget/contents/',
            ],
            'get',
            dataverse_get_widget_contents,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/files/<path:path>/info/',
                '/project/<pid>/node/<nid>/dataverse/files/<path:path>/info/',
            ],
            'get',
            views.crud.dataverse_get_file_info,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}