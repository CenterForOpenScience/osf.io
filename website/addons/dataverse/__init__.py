from .model import AddonDataverseUserSettings, AddonDataverseNodeSettings, \
    DataverseFile
from .routes import settings_routes, page_routes, api_routes
import views

MODELS = [AddonDataverseNodeSettings, AddonDataverseUserSettings, DataverseFile]
USER_SETTINGS_MODEL = AddonDataverseUserSettings
NODE_SETTINGS_MODEL = AddonDataverseNodeSettings

ROUTES = [settings_routes, page_routes, api_routes]

SHORT_NAME = 'dataverse'
FULL_NAME = 'Dataverse'

OWNERS = ['user', 'node']

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = []
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

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.dataverse_hgrid_root

MAX_FILE_SIZE = 10  # MB