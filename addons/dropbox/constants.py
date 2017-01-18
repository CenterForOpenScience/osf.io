from . import routes, views

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

NODE_SETTINGS_TEMPLATE = None  # use default node settings template
USER_SETTINGS_TEMPLATE = None  # use default user settings template
