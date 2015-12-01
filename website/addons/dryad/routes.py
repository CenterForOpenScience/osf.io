# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer
from website.addons.dryad import views
from website.routes import OsfWebRenderer
import os

TEMPLATE_DIR='../addons/dryad/templates/'


settings_routes = {
    'rules':[

    ],
    'prefix': '/api/v1'
}

api_routes ={
    'rules': [
        Rule(
            [
                '/project/<pid>/dryad/widget/',
                '/project/<pid>/node/<nid>/dryad/widget/',
            ],
            'get',
            views.widget.dryad_widget,
            OsfWebRenderer('../addons/dryad/templates/dryad_widget.mako'),
        ),

    ],
    'prefix': '/api/v1'
}

page_routes = {'rules':
[
        Rule(
            [
                '/project/<pid>/dryad/browser/',
                '/project/<pid>/node/<nid>/dryad/browser/',
            ],
            'get',
            views.browser.dryad_browser,
            OsfWebRenderer('../addons/dryad/templates/dryad_browser.mako'),

        ),
        Rule(
            [
                '/project/<pid>/dryad/',
                '/project/<pid>/node/<nid>/dryad/',
            ],
            'get',
            views.dryad.dryad_page,
            OsfWebRenderer('../addons/dryad/templates/dryad_page.mako'),
        ),
        Rule(
            [
                '/project/<pid>/dryad/add',
                '/project/<pid>/node/<nid>/dryad/add',
            ],
            'get',
            views.dryad.set_dryad_doi,
            OsfWebRenderer('../addons/dryad/templates/dryad_page.mako'),
        ),

]

}