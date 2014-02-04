from . import model
from . import routes
from . import views

MODELS = [model.AddonS3UserSettings, model.AddonS3NodeSettings]
USER_SETTINGS_MODEL = model.AddonS3UserSettings
NODE_SETTINGS_MODEL = model.AddonS3NodeSettings

ROUTES = [routes.settings_routes, routes.nonapi_routes, routes.api_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon Simple Storage Service'


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
        'hgrid-s3.js',
    ],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

HAS_HGRID_FILES = True
GET_HGRID_DUMMY = views.hgrid.s3_dummy_folder
MAX_FILE_SIZE = 1024 ** 1024  # There really shouldnt be a limit...
