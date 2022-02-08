"""
Routes associated with the metadata addon
"""

from framework.routing import Rule, json_renderer
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
            '/project/<pid>/metadata/erad/candidates',
            '/project/<pid>/node/<nid>/metadata/erad/candidates',
        ], 'get', views.metadata_get_erad_candidates, json_renderer),
        Rule([
            '/project/<pid>/metadata/project',
            '/project/<pid>/node/<nid>/metadata/project',
        ], 'get', views.metadata_get_project, json_renderer),
        Rule([
            '/project/<pid>/metadata/project',
            '/project/<pid>/node/<nid>/metadata/project',
        ], 'patch', views.metadata_set_project, json_renderer),
        Rule([
            '/project/<pid>/metadata/files/<path:filepath>',
            '/project/<pid>/node/<nid>/metadata/files/<path:filepath>',
        ], 'get', views.metadata_get_file, json_renderer),
        Rule([
            '/project/<pid>/metadata/files/<path:filepath>',
            '/project/<pid>/node/<nid>/metadata/files/<path:filepath>',
        ], 'patch', views.metadata_set_file, json_renderer),
        Rule([
            '/project/<pid>/metadata/files/<path:filepath>',
            '/project/<pid>/node/<nid>/metadata/files/<path:filepath>',
        ], 'delete', views.metadata_delete_file, json_renderer),
    ],
    'prefix': '/api/v1',
}
