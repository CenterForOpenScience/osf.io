# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer
from website.addons.dryad import views

# Routes for JSON API

api_routes = {'rules':
    [
        Rule(
            [
                '/project/<pid>/dryad/settings',
                '/project/<pid>/node/<nid>/dryad/settings',
            ],
            'get',
            views.dryad_generic_views.get_config(),
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/settings',
                '/project/<pid>/node/<nid>/dryad/settings',
            ],
            'put',
            views.dryad_set_doi,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/metadata',
                '/project/<pid>/node/<nid>/dryad/metadata',
            ],
            'get',
            views.dryad_get_current_metadata,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/list',
                '/project/<pid>/node/<nid>/dryad/list',
            ],
            'get',
            views.dryad_list_objects,
            json_renderer,
            {}
        ),
        Rule(
            [
                '/project/<pid>/dryad/search',
                '/project/<pid>/node/<nid>/dryad/search',
            ],
            'get',
            views.dryad_search_objects,
            json_renderer,
            {}
        ),
        Rule(
            [
                '/project/<pid>/dryad/validate',
                '/project/<pid>/node/<nid>/dryad/validate',
            ],
            'get',
            views.dryad_validate_doi,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/cite',
                '/project/<pid>/node/<nid>/dryad/cite',
            ],
            'get',
            views.dryad_citation,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
