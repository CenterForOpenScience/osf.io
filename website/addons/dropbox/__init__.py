import os

from website.addons.dropbox import model, routes, views


MODELS = [model.DropboxUserSettings, model.DropboxNodeSettings]
USER_SETTINGS_MODEL = model.DropboxUserSettings
NODE_SETTINGS_MODEL = model.DropboxNodeSettings

ROUTES = [routes.auth_routes, routes.api_routes]

SHORT_NAME = 'dropbox'
FULL_NAME = 'Dropbox'


OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']

# TODO: Deprecate in favor of webpack/CommonJS bundles
INCLUDE_JS = {
    'widget': [],
    'page': [],
    'files': []
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.dropbox_root_folder

MAX_FILE_SIZE = 150  # MB

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # use default node settings template
USER_SETTINGS_TEMPLATE = None  # use default user settings template
