import os

from .model import AddonDataverseUserSettings, AddonDataverseNodeSettings
from .routes import api_routes
import views

MODELS = [AddonDataverseNodeSettings, AddonDataverseUserSettings]
USER_SETTINGS_MODEL = AddonDataverseUserSettings
NODE_SETTINGS_MODEL = AddonDataverseNodeSettings

ROUTES = [api_routes]

SHORT_NAME = 'dataverse'
FULL_NAME = 'Dataverse'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget']
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
    'files': [],
}

INCLUDE_CSS = {
    'widget': ['dataverse.css'],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views._dataverse_root_folder

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dataverse_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dataverse_user_settings.mako')
