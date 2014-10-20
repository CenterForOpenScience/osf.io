"""

"""

import os

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

TEMPLATE_DIR = '../addons/wiki/templates/'

settings_routes = {
    'rules': [],
    'prefix': '/api/v1',
}

widget_routes = {
    'rules': [
        Rule([
            '/project/<pid>/wiki/widget/',
            '/project/<pid>/node/<nid>/wiki/widget/',
        ], 'get', views.wiki_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

# NOTE: <wname> refers to a wiki page's key, e.g. 'Home'
page_routes = {

    'rules': [

        # Home (Base) | GET
        Rule([
            '/project/<pid>/wiki/',
            '/project/<pid>/node/<nid>/wiki/',
        ], 'get', views.project_wiki_home, OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'wiki.mako'))),

        # View | GET
        Rule([
            '/project/<pid>/wiki/<path:wname>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/',
        ], 'get', views.project_wiki_page, OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'wiki.mako'))),

        # Edit | GET
        Rule([
            '/project/<pid>/wiki/<path:wname>/edit/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/edit/',
        ], 'get', views.project_wiki_edit, OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'edit.mako'))),

        # Edit | POST
        Rule([
            '/project/<pid>/wiki/<path:wname>/edit/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/edit/',
        ], 'post', views.project_wiki_edit_post, OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'edit.mako'))),

        # Compare | GET
        # <wver> refers to a wiki page's version number
        Rule([
            '/project/<pid>/wiki/<path:wname>/compare/<int:wver>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/compare/<int:wver>/',
        ], 'get', views.project_wiki_compare, OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'compare.mako'))),

        # Version : GET
        # <wver> refers to a wiki page's version number
        Rule([
            '/project/<pid>/wiki/<path:wname>/version/<int:wver>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/version/<int:wver>/',
        ], 'get', views.project_wiki_version, OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'compare.mako'))),

    ]

}

api_routes = {

    'rules': [

        # Home (Base) : GET
        Rule([
            '/project/<pid>/wiki/',
            '/project/<pid>/node/<nid>/wiki/',
        ], 'get', views.project_wiki_home, json_renderer),

        # View : GET
        Rule([
            '/project/<pid>/wiki/<path:wname>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/',
        ], 'get', views.project_wiki_page, json_renderer),

        # Content : GET
        Rule([
            '/project/<pid>/wiki/<path:wname>/content/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/content/',
        ], 'get', views.wiki_page_content, json_renderer),

        # Validate | GET
        Rule([
            '/project/<pid>/wiki/<path:wname>/validate/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/validate/',
        ], 'get', views.project_wiki_validate_name, json_renderer),

        # Edit | POST
        Rule([
            '/project/<pid>/wiki/<path:wname>/edit/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/edit/',
        ], 'post', views.project_wiki_edit_post, json_renderer),

        # Rename : PUT
        Rule([
            '/project/<pid>/wiki/<path:wname>/rename/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/rename/',
        ], 'put', views.project_wiki_rename, json_renderer),

        # Compare : GET
        # <wver> refers to a wiki page's version number
        Rule([
            '/project/<pid>/wiki/<path:wname>/compare/<int:wver>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/compare/<int:wver>/',
        ], 'get', views.project_wiki_compare, json_renderer),

        # Version : GET
        # <wver> refers to a wiki page's version number
        Rule([
            '/project/<pid>/wiki/<path:wname>/version/<int:wver>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/version/<int:wver>/',
        ], 'get', views.project_wiki_version, json_renderer),

        # Delete : DELETE
        Rule([
            '/project/<pid>/wiki/<path:wname>/',
            '/project/<pid>/node/<nid>/wiki/<path:wname>/',
        ], 'delete', views.project_wiki_delete, json_renderer),

    ],

    'prefix': '/api/v1',

}
