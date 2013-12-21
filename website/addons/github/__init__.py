from .model.settings import AddonGitHubSettings
from .routes import settings_routes, page_routes

SETTINGS_MODEL = AddonGitHubSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

ADDED_BY_DEFAULT = False

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': ['jquery.githubRepoWidget.min.js'],
    'page': [
        '/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
        '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
        '/static/vendor/dropzone/dropzone.js',
        '/static/js/slickgrid.custom.min.js',
        '/static/js/hgrid.js',
        'hgrid-github.js',
    ],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'GitHub Add-on Alpha'

SCHEMA = {
    'pages': [
        {
            'id': 'null',
            'title': 'GitHub Addon Settings',
            'contents': [
                {
                    'id': 'github_user',
                    'type': 'textfield',
                    'label': 'GitHub User',
                    'required': True,
                },
                {
                    'id': 'github_repo',
                    'type': 'textfield',
                    'label': 'GitHub Repo',
                    'required': True,
                },
            ]
        }
    ]
}
