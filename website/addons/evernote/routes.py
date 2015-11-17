# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.addons.evernote import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/evernote/accounts/',
            ],
            'get',
            views.evernote_get_user_accounts,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1',
}


"""
urlpatterns = patterns(
    'oauth.views',
    url(r"^$", "index", name="evernote_index"),
    url(r"^auth/$", "auth", name="evernote_auth"),
    url(r"^callback/$", "callback", name="evernote_callback"),
    url(r"^reset/$", "reset", name="evernote_auth_reset"),
)
"""