import os

from website.addons.fedora import model, routes, views


MODELS = [model.FedoraUserSettings, model.FedoraNodeSettings]
USER_SETTINGS_MODEL = model.FedoraUserSettings
NODE_SETTINGS_MODEL = model.FedoraNodeSettings

ROUTES = [routes.auth_routes, routes.api_routes]

SHORT_NAME = 'fedora'
FULL_NAME = 'Fedora'


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
GET_HGRID_DATA = views.fedora_root_folder

MAX_FILE_SIZE = 150  # MB

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # use default node settings template
USER_SETTINGS_TEMPLATE = None  # use default user settings template
