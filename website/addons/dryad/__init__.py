import os

from . import routes, views, model

MODELS = [
    model.AddonDryadUserSettings,
    model.AddonDryadNodeSettings,
    model.DryadGuidFile,
]
USER_SETTINGS_MODEL = model.AddonDryadUserSettings
NODE_SETTINGS_MODEL = model.AddonDryadNodeSettings
ROUTES = [routes.api_routes, routes.settings_routes, routes.page_routes]
SHORT_NAME = 'dryad'
FULL_NAME = 'Dryad'
OWNERS = ['user', 'node']
ADDED_DEFAULT = []
ADDED_MANDATORY = []
VIEWS = ['widget','page']
CONFIGS = ['accounts', 'node']
CATEGORIES = ['storage']
INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
HAS_HGRID_FILES = False
GET_HGRID_DATA = None
MAX_FILE_SIZE=1000
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dryad_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dryad_user_settings.mako')


