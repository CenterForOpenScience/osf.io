"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/s3/',
            '/project/<pid>/node/<nid>/settings/s3/',
        ], 'post', views.s3_settings, json_renderer),
    ],
    'prefix': '/api/v1',
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
            '/project/<pid>/s3/upload/<path:path>',
            '/project/<pid>/node/<nid>/s3/upload/',
            '/project/<pid>/node/<nid>/s3/upload/<path:path>',
        ], 'post', views.s3_upload, json_renderer),
        Rule([
            '/project/<pid>/s3/delete/',
            '/<pid>/s3/delete/',
            '/project/<pid>/node/<nid>/s3/delete/',
        ], 'delete', views.s3_delete, json_renderer),
    ],
}

