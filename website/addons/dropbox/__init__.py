from website.addons.dropbox import model, routes


MODELS = [model.DropboxUserSettings]
USER_SETTINGS_MODEL = model.DropboxUserSettings
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
