from website.addons.box import model, routes, utils


MODELS = [
    model.BoxFile,
    model.BoxUserSettings,
    model.BoxNodeSettings,
    model.BoxOAuthSettings,
]

USER_SETTINGS_MODEL = model.BoxUserSettings
NODE_SETTINGS_MODEL = model.BoxNodeSettings

ROUTES = [routes.auth_routes, routes.api_routes]

SHORT_NAME = 'box'
FULL_NAME = 'Box'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

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
GET_HGRID_DATA = utils.box_addon_folder

# MAX_FILE_SIZE = 5  # MB
