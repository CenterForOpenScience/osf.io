"""

"""

from framework.routing import Rule, json_renderer
from website.osf_web_renderer import OsfWebRenderer

from . import views

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/zotero/widget/',
            '/project/<pid>/node/<nid>/zotero/widget/',
        ], 'get', views.zotero_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/zotero/settings/',
            '/project/<pid>/node/<nid>/zotero/settings/',
        ], 'post', views.zotero_set_config, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/zotero/',
            '/project/<pid>/node/<nid>/zotero/',
        ], 'get', views.zotero_page, OsfWebRenderer('../addons/zotero/templates/zotero_page.mako')),
    ],
}
