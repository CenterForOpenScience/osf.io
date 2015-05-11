"""

"""

from framework.routing import Rule, json_renderer
from website.addons.dataverse.views.widget import dataverse_get_widget_contents, \
    dataverse_widget
from website.routes import OsfWebRenderer

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
        ], 'post', views.config.set_dataverse_and_dataset, json_renderer),
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
            views.config.dataverse_add_external_account,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}

api_routes = {
    'rules': [
        Rule(
            '/settings/dataverse/accounts/',
            'get',
            views.config.dataverse_get_user_accounts,
            json_renderer,
        ),
        Rule(
            ['/project/<pid>/dataverse/config/get-datasets/',
            '/project/<pid>/node/<nid>/dataverse/config/get-datasets/'],
            'post',
            views.config.dataverse_get_datasets,
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
                '/project/<pid>/dataverse/hgrid/root/',
                '/project/<pid>/node/<nid>/dataverse/hgrid/root/',
            ],
            'get',
            views.hgrid.dataverse_root_folder_public,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/publish/',
                '/project/<pid>/node/<nid>/dataverse/publish/',
            ],
            'put',
            views.crud.dataverse_publish_dataset,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dataverse/publish-both/',
                '/project/<pid>/node/<nid>/dataverse/publish-both/',
            ],
            'put',
            views.crud.dataverse_publish_both,
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
    ],
    'prefix': '/api/v1'
}
