import os

from . import routes, views, model


MODELS = [
    model.AddonDryadNodeSettings,
    model.AddonDryadUserSettings,
]
USER_SETTINGS_MODEL = model.AddonDryadUserSettings
NODE_SETTINGS_MODEL = model.AddonDryadNodeSettings
ROUTES = [routes.page_routes]
SHORT_NAME = 'dryad'
FULL_NAME = 'Dryad'
OWNERS = ['user', 'node']
ADDED_DEFAULT = []
ADDED_MANDATORY = []
VIEWS = ['page']
CONFIGS = ['accounts', 'node']
CATEGORIES = ['storage']
INCLUDE_JS = {}
INCLUDE_CSS = {}
HAS_HGRID_FILES = True
GET_HGRID_DATA = views.dryad_addon_folder
MAX_FILE_SIZE = 1000
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dryad_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dryad_user_settings.mako')
