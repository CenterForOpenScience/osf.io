from . import model
from . import routes
from . import views

MODELS = [
    model.AddonAppUserSettings,
    model.AddonAppNodeSettings,
]
USER_SETTINGS_MODEL = model.AddonAppUserSettings
NODE_SETTINGS_MODEL = model.AddonAppNodeSettings

ROUTES = [routes.api_routes, routes.web_routes]

SHORT_NAME = 'app'
FULL_NAME = 'Application'

OWNERS = ['node']

VIEWS = []
CONFIGS = ['node']

CATEGORIES = ['service']

INCLUDE_JS = {
    'page': [],
    'files': []
}

INCLUDE_CSS = {
    'page': [],
    'files': []
}

HAS_HGRID_FILES = False
