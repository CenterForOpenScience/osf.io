from .model import AddonDataverseUserSettings, AddonDataverseNodeSettings
from .routes import settings_routes, page_routes

MODELS = [AddonDataverseNodeSettings, AddonDataverseUserSettings]
USER_SETTINGS_MODEL = AddonDataverseUserSettings
NODE_SETTINGS_MODEL = AddonDataverseNodeSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'dataverse'
FULL_NAME = 'Dataverse'

OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget', 'page']
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
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
