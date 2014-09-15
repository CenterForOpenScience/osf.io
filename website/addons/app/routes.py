# -*- coding: utf-8 -*-
"""Routes for the app addon.
"""

from framework.routing import Rule, json_renderer
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


    #     ##### Download file #####
    #     Rule(
    #         [
    #             '/project/<pid>/app/files/<path:path>/download/',
    #             '/project/<pid>/node/<nid>/app/files/<path:path>/download/',
    #         ],
    #         'get',
    #         views.crud.app_download,
    #         notemplate,
    #     ),
    ],
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
                '/project/<pid>/app/reports/',
                '/project/<pid>/node/<nid>/app/reports/'
            ],
            'post',
            views.crud.create_report,
            json_renderer
        )

    ],

    ## Your routes here

    'prefix': '/api/v1'
}


custom_routing_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/app/',
             '/project/<pid>/node/<nid>/app/'],
            'get',
            views.crud.query_app,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/',
             '/project/<pid>/node/<nid>/app/routes/'],
            'get',
            views.crud.list_custom_routes,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/',
             '/project/<pid>/node/<nid>/app/routes/'],
            'post',
            views.crud.create_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/<path:route>/',
             '/project/<pid>/node/<nid>/app/routes/<path:route>/'],
            'get',
            views.crud.resolve_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/<path:route>/',
             '/project/<pid>/node/<nid>/app/routes/<path:route>/'],
            'put',
            views.crud.update_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/routes/<path:route>/',
             '/project/<pid>/node/<nid>/app/routes/<path:route>/'],
            'delete',
            views.crud.delete_route,
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
            views.crud.get_metadata,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            ['put', 'post'],
            views.crud.add_metadata,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            'delete',
            views.crud.delete_metadata,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
