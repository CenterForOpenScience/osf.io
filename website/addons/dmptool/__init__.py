import os

from .model import AddonDmptoolUserSettings, AddonDmptoolNodeSettings
from .routes import api_routes
import views

MODELS = [AddonDmptoolNodeSettings, AddonDmptoolUserSettings]
USER_SETTINGS_MODEL = AddonDmptoolUserSettings
NODE_SETTINGS_MODEL = AddonDmptoolNodeSettings

ROUTES = [api_routes]

SHORT_NAME = 'dmptool'
FULL_NAME = 'Dmptool'

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
    'widget': ['dmptool.css'],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views._dmptool_root_folder

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dmptool_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'dmptool_user_settings.mako')