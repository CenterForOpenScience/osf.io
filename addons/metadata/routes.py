# -*- coding: utf-8 -*-
"""
Routes associated with the metadata addon
"""

from framework.routing import Rule, json_renderer
from website.routes import notemplate
from . import SHORT_NAME
from . import views

api_routes = {
    'rules': [
        Rule([
            '/settings/{}/erad'.format(SHORT_NAME),
        ], 'get', views.metadata_get_user_erad_config, json_renderer),
        Rule([
            '/settings/{}/erad'.format(SHORT_NAME),
        ], 'put', views.metadata_set_user_erad_config, json_renderer),
        Rule([
            '/project/<pid>/{}/erad/candidates'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/erad/candidates'.format(SHORT_NAME),
        ], 'get', views.metadata_get_erad_candidates, json_renderer),
        Rule([
            '/project/<pid>/{}/project'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/project'.format(SHORT_NAME),
        ], 'get', views.metadata_get_project, json_renderer),
        Rule([
            '/project/<pid>/{}/schemas'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/schemas'.format(SHORT_NAME),
        ], 'get', views.metadata_get_schemas, json_renderer),
        Rule([
            '/project/<pid>/{}/files/<path:filepath>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/files/<path:filepath>'.format(SHORT_NAME),
        ], 'get', views.metadata_get_file, json_renderer),
        Rule([
            '/project/<pid>/{}/files/<path:filepath>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/files/<path:filepath>'.format(SHORT_NAME),
        ], 'patch', views.metadata_set_file, json_renderer),
        Rule([
            '/project/<pid>/{}/files/<path:filepath>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/files/<path:filepath>'.format(SHORT_NAME),
        ], 'delete', views.metadata_delete_file, json_renderer),
        Rule([
            '/project/<pid>/{}/hashes/<path:filepath>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/hashes/<path:filepath>'.format(SHORT_NAME),
        ], 'patch', views.metadata_set_file_hash, json_renderer),
        Rule([
            '/project/<pid>/{}/draft_registrations/<did>/files/<mnode>/<path:filepath>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/draft_registrations/<did>/files/<mnode>/<path:filepath>'.format(SHORT_NAME),
        ], 'put', views.metadata_set_file_to_drafts, json_renderer),
        Rule([
            '/project/<pid>/{}/draft_registrations/<did>/files/<mnode>/<path:filepath>'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/draft_registrations/<did>/files/<mnode>/<path:filepath>'.format(SHORT_NAME),
        ], 'delete', views.metadata_delete_file_from_drafts, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule(
            [
                '/<pid>/{}'.format(SHORT_NAME),
                '/<pid>/node/<nid>/{}'.format(SHORT_NAME),
            ],
            'get',
            views.metadata_report_list_view,
            notemplate
        ),
        Rule(
            [
                '/<pid>/{}/draft_registrations/<did>/csv'.format(SHORT_NAME),
                '/<pid>/node/<nid>/{}/draft_registrations/<did>/csv'.format(SHORT_NAME),
            ],
            'get',
            views.metadata_export_draft_registrations_csv,
            notemplate
        ),
        Rule(
            [
                '/<pid>/{}/registrations/<rid>/csv'.format(SHORT_NAME),
                '/<pid>/node/<nid>/{}/registrations/<rid>/csv'.format(SHORT_NAME),
            ],
            'get',
            views.metadata_export_registrations_csv,
            notemplate
        ),
    ]
}
