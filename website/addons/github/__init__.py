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

VIEWS = []
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
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'GitHub Add-on Alpha'

GET_HGRID_DATA = views.github_hgrid_data
GET_HGRID_DUMMY = views.github_dummy_folder
