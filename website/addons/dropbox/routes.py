from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
    ],
    'prefix': '/api/v1/'
}

api_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/dropbox/<path:path>/delete/',
                '/project/<pid>/node/<nid>/dropbox/<path:path>/delete/',
            ],
            'delete',
            views.crud.dropbox_delete_file,
            json_renderer
        ),
    ],
    'prefix': '/api/v1/'
}

nonapi_routes = {
    'rules': [
    ]
}
