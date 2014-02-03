from . import routes, views, model

MODELS = [
    model.AddonGitHubUserSettings,
    model.AddonGitHubNodeSettings,
    model.GithubGuidFile,
]
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
        '/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
        '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
        '/static/vendor/dropzone/dropzone.js',
        '/static/js/slickgrid.custom.min.js',
        '/static/js/hgrid.js',
        'hgrid-github.js',
    ],
    'files': [
        'hgrid-files.js',
    ]
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'GitHub Add-on Alpha'

HAS_HGRID_FILES = True
GET_HGRID_DUMMY = views.hgrid.github_dummy_folder

MAX_FILE_SIZE = 1024 * 1024
