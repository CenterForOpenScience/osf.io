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
            '/app/<pid>/auth/',
            'post',
            views.crud.get_access,
            json_renderer
        ),
        Rule(
            '/app/<pid>/projects/',
            'post',
            views.crud.create_application_project,
            json_renderer
        ),
        Rule(
            '/app/<pid>/projects/<guid>/',
            'get',
            views.crud.get_project_metadata,
            json_renderer
        ),
        Rule(
            '/app/<pid>/<path:route>/',
            ['post', 'put', 'get', 'delete'],
            views.crud.act_as_application,
            json_renderer
        ),
        Rule(
            '/app/<pid>/',
            'post',
            views.crud.query_app_json,
            json_renderer
        ),
        Rule(
            '/app/<pid>/',
            'get',
            views.crud.query_app,
            json_renderer
        ),
        Rule(
            '/app/<pid>/projects/<apid>/',
            'put',
            views.crud.update_application_project,
            json_renderer
        ),
        Rule(
            '/app/<pid>/rss/',
            'get',
            views.crud.query_app_rss,
            xml_renderer
        ),
        Rule(
            '/app/<pid>/atom/',
            'get',
            views.crud.query_app_atom,
            xml_renderer
        ),
        Rule(
            '/app/<pid>/resync/resourcelist/',
            'get',
            views.crud.query_app_resourcelist,
            xml_renderer
        ),
        Rule(
            '/app/<pid>/resync/changelist/',
            'get',
            views.crud.query_app_changelist,
            xml_renderer
        ),
        Rule(
            '/app/<pid>/resync/capabilitylist/',
            'get',
            views.crud.query_app_capabilitylist,
            xml_renderer
        ),
        Rule(
            '/app/<pid>/mapping/',
            'get',
            views.crud.get_mapping,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}


custom_routing_routes = {
    'rules': [
        Rule(
            '/app/<pid>/routes/',
            'get',
            views.crud.customroutes.list_custom_routes,
            json_renderer
        ),
        Rule(
            '/app/<pid>/routes/',
            'post',
            views.crud.customroutes.create_route,
            json_renderer
        ),
        Rule(
            '/app/<pid>/routes/<path:route>/',
            'get',
            views.crud.customroutes.resolve_route,
            json_renderer
        ),
        Rule(
            '/app/<pid>/routes/<path:route>/rss/',
            'get',
            views.crud.customroutes.resolve_route_rss,
            xml_renderer
        ),
        Rule(
            '/app/<pid>/routes/<path:route>/',
            'put',
            views.crud.customroutes.update_route,
            json_renderer
        ),
        Rule(
            '/app/<pid>/routes/<path:route>/',
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
            '/app/<pid>/metadata/schema/types/',
            'get',
            views.crud.metadata.get_schema_types,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/schema/',
            'get',
            views.crud.metadata.get_schema,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/schema/',
            'post',
            views.crud.metadata.post_schema,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/schema/',
            'delete',
            views.crud.metadata.delete_schema,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/',
            'get',
            views.crud.metadata.get_metadata_ids,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/',
            'post',
            views.crud.metadata.create_metadata,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/<mid>/',
            'get',
            views.crud.metadata.get_metadata,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/<mid>/',
            'put',
            views.crud.metadata.update_metadata,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/<mid>/',
            'delete',
            views.crud.metadata.delete_metadata,
            json_renderer
        ),
        Rule(
            '/app/<pid>/metadata/<mid>/promote/',
            'post',
            views.crud.metadata.promote_metadata,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
