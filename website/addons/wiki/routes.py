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

page_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/wiki/',
                '/project/<pid>/node/<nid>/wiki/',
            ],
            'get',
            views.project_wiki_home,
            OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'wiki.mako')),
        ),

        # View
        Rule(
            [
                '/project/<pid>/wiki/<wid>/',
                '/project/<pid>/node/<nid>/wiki/<wid>/',
            ],
            'get',
            views.project_wiki_page,
            OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'wiki.mako')),
        ),

        # Edit | GET
        Rule(
            [
                '/project/<pid>/wiki/<wid>/edit/',
                '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
            ],
            'get',
            views.project_wiki_edit,
            OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'edit.mako')),
        ),

        # Edit | POST
        Rule(
            [
                '/project/<pid>/wiki/<wid>/edit/',
                '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
            ],
            'post',
            views.project_wiki_edit_post,
            OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'edit.mako')),
        ),


        # Compare
        Rule(
            [
                '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
                '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
            ],
            'get',
            views.project_wiki_compare,
            OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'compare.mako')),
        ),

        # Versions
        Rule(
            [
                '/project/<pid>/wiki/<wid>/version/<vid>/',
                '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
            ],
            'get',
            views.project_wiki_version,
            OsfWebRenderer(os.path.join(TEMPLATE_DIR, 'compare.mako')),
        ),

    ]

}

api_routes = {

    'rules': [

        # View
        Rule([
            '/project/<pid>/wiki/<wid>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/',
        ], 'get', views.project_wiki_page, json_renderer),

        #justcontent
        Rule([
            '/project/<pid>/wiki/content/<wid>/',
            '/project/<pid>/node/<nid>/wiki/content/<wid>/',
        ], 'get', views.wiki_page_content, json_renderer),

        # Edit | POST
        Rule([
            '/project/<pid>/wiki/<wid>/edit/',
            '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
        ], 'post', views.project_wiki_edit_post, json_renderer),

        # Rename
        Rule(
            [
                '/project/<pid>/wiki/<wid>/rename/',
                '/project/<pid>/node/<nid>/wiki/<wid>/rename/',
            ],
            'put',
            views.project_wiki_rename,
            json_renderer,
        ),

        # Compare
        Rule([
            '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
        ], 'get', views.project_wiki_compare, json_renderer),

        # Versions
        Rule([
            '/project/<pid>/wiki/<wid>/version/<vid>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
        ], 'get', views.project_wiki_version, json_renderer),

    ],

    'prefix': '/api/v1',

}
