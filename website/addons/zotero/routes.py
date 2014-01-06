"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/zotero/',
            '/project/<pid>/node/<nid>/settings/zotero/',
        ], 'post', views.zotero_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/zotero/',
            '/project/<pid>/node/<nid>/settings/zotero/',
        ], 'post', views.zotero_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/zotero/',
            '/project/<pid>/node/<nid>/zotero/',
        ], 'get', views.zotero_page, OsfWebRenderer('project/addon/addon.mako')),
    ],
}
