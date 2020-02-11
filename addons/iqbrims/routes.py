# -*- coding: utf-8 -*-
"""Routes for the iqbrims addon.
"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

TEMPLATE_DIR = './addons/iqbrims/templates/'

# HTML endpoints
page_routes = {

    'rules': [

        # Home (Base) | GET
        Rule(
            [
                '/<pid>/iqbrims',
                '/<pid>/node/<nid>/iqbrims',
            ],
            'get',
            views.project_iqbrims,
            OsfWebRenderer('page.mako', trust=False, template_dir=TEMPLATE_DIR)
        ),

    ]
}

# JSON endpoints
api_routes = {
    'rules': [

        #### Profile settings ###

        Rule(
            [
                '/settings/iqbrims/accounts/',
            ],
            'get',
            views.iqbrims_account_list,
            json_renderer,

        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/iqbrims/folders/',
             '/project/<pid>/node/<nid>/iqbrims/folders/'],
            'get',
            views.iqbrims_folder_list,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/',
             '/project/<pid>/node/<nid>/iqbrims/config/'],
            'get',
            views.iqbrims_get_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/',
             '/project/<pid>/node/<nid>/iqbrims/config/'],
            'put',
            views.iqbrims_set_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/',
             '/project/<pid>/node/<nid>/iqbrims/config/'],
            'delete',
            views.iqbrims_deauthorize_node,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/import-auth/',
             '/project/<pid>/node/<nid>/iqbrims/config/import-auth/'],
            'put',
            views.iqbrims_import_auth,
            json_renderer
        ),

        Rule([
            '/project/<pid>/iqbrims/status',
            '/project/<pid>/node/<nid>/iqbrims/status',
        ], 'get', views.iqbrims_get_status, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/status',
            '/project/<pid>/node/<nid>/iqbrims/status',
        ], 'patch', views.iqbrims_set_status, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/notify',
            '/project/<pid>/node/<nid>/iqbrims/notify',
        ], 'post', views.iqbrims_post_notify, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/workflow/<part>/state',
            '/project/<pid>/node/<nid>/iqbrims/workflow/<part>/state',
        ], 'post', views.iqbrims_post_workflow_state, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/storage/<folder>',
            '/project/<pid>/node/<nid>/iqbrims/storage/<folder>',
        ], 'get', views.iqbrims_get_storage, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/storage/<folder>',
            '/project/<pid>/node/<nid>/iqbrims/storage/<folder>',
        ], 'delete', views.iqbrims_reject_storage, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/index',
            '/project/<pid>/node/<nid>/iqbrims/index',
        ], 'put', views.iqbrims_create_index, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/index',
            '/project/<pid>/node/<nid>/iqbrims/index',
        ], 'delete', views.iqbrims_close_index, json_renderer),

        Rule([
            '/project/<pid>/iqbrims/filelist/<folder>',
            '/project/<pid>/node/<nid>/iqbrims/filelist/<folder>',
        ], 'put', views.iqbrims_create_filelist, json_renderer),

    ],
    'prefix': '/api/v1'
}
