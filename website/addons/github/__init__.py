from .model import AddonGitHubUserSettings, AddonGitHubNodeSettings
from .routes import settings_routes, page_routes

USER_SETTINGS_MODEL = AddonGitHubUserSettings
NODE_SETTINGS_MODEL = AddonGitHubNodeSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget', 'page']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': ['jquery.githubRepoWidget.js'],
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
