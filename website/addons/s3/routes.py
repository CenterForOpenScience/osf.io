"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from website.addons.s3 import views

#TODO clean me up redo naming scheme

node_settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/s3/settings/',
            '/project/<pid>/node/<nid>/s3/settings/',
        ], 'post', views.config.s3_settings, json_renderer),
        Rule([
            '/project/<pid>/s3/settings/delete/',
            '/api/v1/project/<pid>/s3/settings/delete/',
            '/project/<pid>/node/<nid>/s3/settings/delete/',
        ], 'post', views.config.s3_delete_access_key, json_renderer),
    ],
    'prefix': '/api/v1',
}

user_settings_routes = {
    'rules': [
        Rule([
            '/settings/s3/',
        ], 'post', views.config.s3_user_settings, json_renderer),
        Rule([
            '/settings/s3/delete/',
        ], 'post', views.config.s3_remove_user_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/s3/',
            '/project/<pid>/node/<nid>/s3/',
        ], 'get', views.crud.s3_page, OsfWebRenderer('../addons/s3/templates/s3_page.mako')),
        Rule([
            '/project/<pid>/s3/fetchurl/<key>',
            '/project/<pid>/node/<nid>/s3/fetchurl/<key>',
            ], 'get', views.crud.s3_download, json_renderer),
        Rule([
            '/project/<pid>/s3/delete/',
            '/<pid>/s3/delete/',
            '/project/<pid>/node/<nid>/s3/delete/',
        ], 'delete', views.crud.s3_delete, json_renderer),
        Rule([
            '/project/<pid>/s3/render/<key>',
            '/project/<pid>/node/<nid>/s3/render/<key>'
        ],'get', views.crud.render_file, OsfWebRenderer('../addons/s3/templates/s3_render.mako')),
        Rule([
            '/project/<pid>/s3/newfolder/<path>',
            '/project/<pid>/node/<nid>/s3/newfolder/<path>'
        ],'get', views.crud.s3_new_folder, json_renderer),
        Rule([
            '/project/<pid>/s3/getsigned/',
            '/project/<pid>/node/<nid>/s3/getsigned/'
        ],'post', views.utils.generate_signed_url, json_renderer),
    ],
    'prefix': '/api/v1',
}
