from .model import AddonS3UserSettings, AddonS3NodeSettings
from .routes import node_settings_routes, user_settings_routes, page_routes, crud_routes, hgrid_routes
from . import views

MODELS = [AddonS3UserSettings, AddonS3NodeSettings]
USER_SETTINGS_MODEL = AddonS3UserSettings
NODE_SETTINGS_MODEL = AddonS3NodeSettings

ROUTES = [node_settings_routes, user_settings_routes, page_routes, crud_routes, hgrid_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon Simple Storage Service'


OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = []#['page']
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

HAS_HGRID_FILES = True
GET_HGRID_DUMMY = views.hgrid.s3_dummy_folder
MAX_FILE_SIZE = 1024 ** 1024  #This might actually need to be smaller.....
