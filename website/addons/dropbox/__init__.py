from . import model
from . import routes
from . import views

MODELS = [model.AddonDropboxUserSettings] #  TODO Other models needed? , model.AddonDropboxNodeSettings, model.DropboxGuidFile]
USER_SETTINGS_MODEL = model.AddonDropboxNodeSettings
#NODE_SETTINGS_MODEL = model.AddonDropboxNodeSettings

ROUTES = [routes.settings_routes, routes.nonapi_routes, routes.api_routes]

SHORT_NAME = 'dropbox'
FULL_NAME = 'Dropbox'


OWNERS = ['user']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user']

CATEGORIES = ['storage']

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
# GET_HGRID_DATA = TODO

MAX_FILE_SIZE = 5  # MB
