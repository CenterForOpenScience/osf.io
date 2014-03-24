from website.routes import OsfWebRenderer
from framework.routing import Rule, json_renderer

from . import views


widget_route = {
    'rules': [
        Rule([
            '/project/<pid>/badges/widget/',
            '/project/<pid>/node/<nid>/badges/widget/',
        ], 'get', views.badges_widget, json_renderer),
    ],
    'prefix': '/api/v1',
}

api_urls = {
    'rules': [
        Rule('/badges/new/', 'post', views.create_badge, json_renderer),
        Rule('/settings/badges/', 'post', views.create_organization, json_renderer),
        Rule([
            '/project/<pid>/badges/award/',
            '/project/<pid>/node/<nid>/badges/award/',
        ], 'post', views.award_badge, json_renderer),
        Rule([
            '/project/<pid>/badges/revoke/',
            '/project/<pid>/node/<nid>/badges/revoke/',
        ], 'post', views.revoke_badge, json_renderer),
    ],
    'prefix': '/api/v1',
}

guid_urls = {
    'rules': [
        Rule([
            '/badge/<bid>/',
        ], 'get', views.get_badge, OsfWebRenderer('../addons/badges/templates/view_badge.mako')),
        Rule([
            '/badge/<bid>/json/',
        ], 'get', views.get_badge_json, json_renderer),
        Rule([
            '/badge/assertions/<aid>/',
        ], 'get', views.get_assertion, OsfWebRenderer('../addons/badges/templates/view_assertion.mako')),
        Rule([
            '/badge/assertions/<aid>/',
        ], 'get', views.get_assertion, json_renderer),
        Rule([
            '/badge/assertions/<aid>/json/',
        ], 'get', views.get_assertion_json, json_renderer),
        Rule([
            '/badge/organization/<uid>/',
        ], 'get', views.get_organization, json_renderer),
        Rule([
            '/badge/organization/<uid>/json/',
        ], 'get', views.get_organization_json, json_renderer),
        Rule([
            '/badge/organization/<uid>/revoked/json/',
        ], 'get', views.get_revoked_json, json_renderer),
    ]
}
