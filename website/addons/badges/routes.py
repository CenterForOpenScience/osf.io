from website.routes import OsfWebRenderer
from framework.routing import Rule, json_renderer

from . import views


render_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/badges/',
                '/project/<pid>/node/<nid>/badges/',
            ],
            'get',
            views.render.badges_page,
            OsfWebRenderer('../addons/badges/templates/badges_page.mako', trust=False)
        ),
    ],
}

api_urls = {
    'rules': [
        Rule('/badges/new/', 'post', views.crud.create_badge, json_renderer),
        Rule(
            '/dashboard/get_badges/',
            'get', views.render.dashboard_badges, json_renderer),
        Rule(
            '/dashboard/get_assertions/',
            'get', views.render.dashboard_assertions, json_renderer),
        Rule(
            '/profile/<uid>/badges/json/',
            'get', views.render.organization_badges_listing, json_renderer),
        Rule([
            '/project/<pid>/badges/award/',
            '/project/<pid>/node/<nid>/badges/award/',
        ], 'post', views.crud.award_badge, json_renderer),
        Rule([
            '/project/<pid>/badges/revoke/',
            '/project/<pid>/node/<nid>/badges/revoke/',
        ], 'post', views.crud.revoke_badge, json_renderer),
        Rule([
            '/project/<pid>/badges/widget/',
            '/project/<pid>/node/<nid>/badges/widget/',
        ], 'get', views.render.badges_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

guid_urls = {
    'rules': [
        Rule(
            '/badge/<bid>/',
            'get',
            views.render.view_badge,
            OsfWebRenderer('../addons/badges/templates/view_badge.mako', trust=False)
        ),
        Rule(
            '/badge/<bid>/json/',
            'get', views.openbadge.get_badge_json, json_renderer),
        Rule(
            '/badge/assertion/json/<aid>/',
            'get', views.openbadge.get_assertion_json, json_renderer),
        Rule(
            '/badge/organization/<uid>/json/',
            'get', views.openbadge.get_organization_json, json_renderer),
    ]
}
