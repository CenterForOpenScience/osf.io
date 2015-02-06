from . import model
from . import routes

MODELS = [
    model.AddonMendeleyUserSettings,
    model.AddonMendeleyNodeSettings,
]


USER_SETTINGS_MODEL = model.AddonMendeleyUserSettings
NODE_SETTINGS_MODEL = model.AddonMendeleyNodeSettings

ROUTES = [routes.api_routes]

SHORT_NAME = 'mendeley'
FULL_NAME = 'Mendeley'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget']
CONFIGS = ['user', 'node']

CATEGORIES = ['citations']

INCLUDE_JS = {}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
    'files': []
}

WIDGET_HELP = 'Mendeley'

HAS_HGRID_FILES = False
