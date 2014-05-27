from .model import AddonDataverseUserSettings, AddonDataverseNodeSettings, \
    DataverseFile
from .routes import settings_routes, page_routes, api_routes
import views

MODELS = [AddonDataverseNodeSettings, AddonDataverseUserSettings, DataverseFile]
USER_SETTINGS_MODEL = AddonDataverseUserSettings
NODE_SETTINGS_MODEL = AddonDataverseNodeSettings

ROUTES = [settings_routes, page_routes, api_routes]

SHORT_NAME = 'dataverse'
FULL_NAME = 'Dataverse'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': ['dataverse-rubeus-cfg.js'],
    'page': [],
    'files': ['dataverse-rubeus-cfg.js'],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.dataverse_hgrid_root

# MAX_FILE_SIZE = 10  # MB