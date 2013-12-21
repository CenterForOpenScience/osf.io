"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from .views import zotero_settings, zotero_disable, zotero_page

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/zotero/',
            '/project/<pid>/node/<nid>/settings/zotero/',
        ], 'post', zotero_settings, json_renderer),
    ],
    'prefix': '/api/v1',
}

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/zotero/',
            '/project/<pid>/node/<nid>/settings/zotero/',
        ], 'post', zotero_settings, json_renderer),
        Rule([
            '/project/<pid>/settings/zotero/disable/',
            '/project/<pid>/node/<nid>/settings/zotero/disable/',
        ], 'post', zotero_disable, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/zotero/',
            '/project/<pid>/node/<nid>/zotero/',
        ], 'get', zotero_page, OsfWebRenderer('project/addon.mako')),
    ],
}
