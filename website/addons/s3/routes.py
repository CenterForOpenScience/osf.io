"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/s3/settings/',
            '/project/<pid>/node/<nid>/s3/settings/',
        ], 'post', views.s3_settings, json_renderer),
        Rule([
            '/user/s3/settings/',
        ], 'post', views.s3_user_settings, json_renderer),
    ],
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/s3/',
            '/project/<pid>/node/<nid>/s3/',
        ], 'get', views.s3_page, OsfWebRenderer('../addons/s3/templates/s3_page.mako')),
        Rule([
            '/project/<pid>/s3/fetchurl/<key>',
            '/project/<pid>/node/<nid>/s3/fetchurl/<key>',
            ], 'get', views.s3_download, json_renderer),
        Rule([
            '/project/<pid>/s3/upload/',
            '/project/<pid>/s3/upload/<path>',
            '/project/<pid>/node/<nid>/s3/upload/',
            '/project/<pid>/node/<nid>/s3/upload/<path>',
        ], 'post', views.s3_upload, json_renderer),
        Rule([
            '/project/<pid>/s3/delete/',
            '/<pid>/s3/delete/',
            '/project/<pid>/node/<nid>/s3/delete/',
        ], 'delete', views.s3_delete, json_renderer),
        Rule([
            '/project/<pid>/s3/render/<key>',
            '/project/<pid>/node/<nid>/s3/render/<key>'
        ],'get',views.render_file, OsfWebRenderer('../addons/s3/templates/s3_render.mako')),
        Rule([
            '/project/<pid>/s3/newfolder/<path>',
            '/project/<pid>/node/<nid>/s3/newfolder/<path>'
        ],'get',views.s3_new_folder, json_renderer),
        Rule([
            '/project/<pid>/s3/makeKey/',
            '/project/<pid>/node/<nid>/s3/makekey/'
        ],'post',views.s3_create_access_key, json_renderer),
    ],
}

user_settings_routes = {
    'rules' : [
         Rule([
            '/project/<pid>/s3/makeKey/',
            '/project/<pid>/node/<nid>/s3/makekey/'
        ],'post',views.s3_create_access_key, json_renderer),
         Rule([
            '/project/<pid>/s3/key/delete',
            '/project/<pid>/node/<nid>/s3/key/delete'
        ],'post',views.s3_delete_access_key, json_renderer),
    ],
    'prefix': '/api/v1',
}
