# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer
from website.addons.dryad import views
from website.routes import OsfWebRenderer
import os

TEMPLATE_DIR='../addons/dryad/templates/'


page_routes = {'rules':
[
        Rule(
            [
                '/project/<pid>/dryad/browser',
                '/project/<pid>/node/<nid>/dryad/browser',
            ],
            'get',
            views.dryad_browser,
            OsfWebRenderer('../addons/dryad/templates/dryad_page.mako'),

        ),
        Rule(
            [
                '/project/<pid>/dryad/',
                '/project/<pid>/node/<nid>/dryad/',
            ],
            'get',
            views.dryad_page,
            OsfWebRenderer('../addons/dryad/templates/dryad_page.mako'),
        ),
        Rule(
            [
                '/project/<pid>/dryad/search',
                '/project/<pid>/node/<nid>/dryad/search',
            ],
            'get',
            views.search_dryad_page,
            OsfWebRenderer('../addons/dryad/templates/dryad_page.mako'),
        ),
        Rule(
            [
                '/project/<pid>/dryad/check',
                '/project/<pid>/node/<nid>/dryad/check',
            ],
            'get',
            views.check_dryad_doi,
            OsfWebRenderer('../addons/dryad/templates/dryad_check_doi.mako'),
        ),
        Rule(
            [
                '/project/<pid>/dryad/add',
                '/project/<pid>/node/<nid>/dryad/add',
            ],
            'get',
            views.set_dryad_doi,
            OsfWebRenderer('../addons/dryad/templates/dryad_page.mako'),
        ),
        Rule(
            [
                '/project/<pid>/dryad/rm',
                '/project/<pid>/node/<nid>/dryad/rm',
            ],
            'get',
            views.remove_dryad_doi,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/dryad/hgrid/root/',
                '/project/<pid>/node/<nid>/dryad/hgrid/root/',
            ],
            'get',
            views.dryad_addon_folder,
            json_renderer,
        ),

],
    'prefix': '/api/v1'
}