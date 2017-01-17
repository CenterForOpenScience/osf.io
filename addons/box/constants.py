from . import routes, views

ROUTES = [routes.api_routes]

SHORT_NAME = 'box'
FULL_NAME = 'Box'

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
GET_HGRID_DATA = views.box_root_folder

MAX_FILE_SIZE = 250  # MB

NODE_SETTINGS_TEMPLATE = None  # use default node settings template
USER_SETTINGS_TEMPLATE = None  # use default user settings template
