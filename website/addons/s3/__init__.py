from .model import AddonS3UserSettings, AddonS3NodeSettings
from .routes import settings_routes, page_routes, user_settings_routes

USER_SETTINGS_MODEL = AddonS3UserSettings
NODE_SETTINGS_MODEL = AddonS3NodeSettings

ROUTES = [settings_routes, page_routes, user_settings_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon Simple Storage Service'


OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['page']
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
        'hgrid-s3.js',
    ],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}
