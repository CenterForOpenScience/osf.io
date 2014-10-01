# -*- coding: utf-8 -*-
"""Routes for the app addon.
"""

from framework.routing import Rule, json_renderer, xml_renderer
from website.routes import OsfWebRenderer

from . import views

# Routes that use the web renderer
web_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/app/',
                '/project/<pid>/node/<nid>/app/',
            ],
            'get',
            views.web.application_page,
            OsfWebRenderer('../addons/app/templates/app_page.mako'),
        ),
    ]
}

# JSON endpoints
api_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/app/projects/',
                '/project/<pid>/node/<nid>/app/projects/'
            ],
            'post',
            views.crud.create_application_project,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/app/<path:route>/',
                '/project/<pid>/node/<nid>/app/<path:route>/'
            ],
            ['post', 'put', 'get', 'delete'],
            views.crud.act_as_application,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/',
             '/project/<pid>/node/<nid>/app/'],
            'get',
            views.crud.query_app,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app.rss',
             '/project/<pid>/node/<nid>/app.rss'],
            'get',
            views.crud.query_app_rss,
            xml_renderer
        ),
    ],
    'prefix': '/api/v1'
}


custom_routing_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/app/routes/',
             '/project/<pid>/node/<nid>/app/routes/'],
            'get',
            views.crud.customroutes.list_custom_routes,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/',
             '/project/<pid>/node/<nid>/app/routes/'],
            'post',
            views.crud.customroutes.create_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/<path:route>/',
             '/project/<pid>/node/<nid>/app/routes/<path:route>/'],
            'get',
            views.crud.customroutes.resolve_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/<path:route>/',
             '/project/<pid>/node/<nid>/app/routes/<path:route>/'],
            'put',
            views.crud.customroutes.update_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/<path:route>/',
             '/project/<pid>/node/<nid>/app/routes/<path:route>/'],
            'delete',
            views.crud.customroutes.delete_route,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}

metadata_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            'get',
            views.crud.metadata.get_metadata,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            ['put', 'post'],
            views.crud.metadata.add_metadata,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            'delete',
            views.crud.metadata.delete_metadata,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
