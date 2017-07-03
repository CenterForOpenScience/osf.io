import os
from . import routes, model

MODELS = [
    model.DryadNodeSettings,
]
USER_SETTINGS_MODEL = None
NODE_SETTINGS_MODEL = model.DryadNodeSettings
ROUTES = [routes.api_routes]
SHORT_NAME = 'dryad'
FULL_NAME = 'Dryad'
OWNERS = ['node']
ADDED_DEFAULT = []
ADDED_MANDATORY = []
VIEWS = []
CONFIGS = ['node']
CATEGORIES = ['citations']
HAS_HGRID_FILES = False
GET_HGRID_DATA = None
MAX_FILE_SIZE = 1000
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dryad_node_settings.mako')
USER_SETTINGS_TEMPLATE = None
