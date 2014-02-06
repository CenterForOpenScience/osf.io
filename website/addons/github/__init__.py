from . import routes, views, model

MODELS = [model.AddonGitHubUserSettings, model.AddonGitHubNodeSettings]
USER_SETTINGS_MODEL = model.AddonGitHubUserSettings
NODE_SETTINGS_MODEL = model.AddonGitHubNodeSettings

ROUTES = [routes.api_routes, routes.settings_routes, routes.page_routes]

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget']
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': ['jquery.githubRepoWidget.js'],
    'page': [
        'hgrid-github.js',
    ],
    'files': [
        'filebrowser-cfg.js',
    ]
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
    'files': ['filebrowser.css']
}

WIDGET_HELP = 'GitHub Add-on Alpha'

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.github_hgrid_data

MAX_FILE_SIZE = 1024 * 1024
