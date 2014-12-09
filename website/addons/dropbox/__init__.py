from website.addons.dropbox import model, routes, views


MODELS = [model.DropboxUserSettings, model.DropboxNodeSettings, model.DropboxFile]
USER_SETTINGS_MODEL = model.DropboxUserSettings
NODE_SETTINGS_MODEL = model.DropboxNodeSettings

ROUTES = [routes.auth_routes, routes.web_routes, routes.api_routes]

SHORT_NAME = 'dropbox'
FULL_NAME = 'Dropbox'


OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

# TODO: Deprecate in favor of webpack/CommonJS bundles
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
GET_HGRID_DATA = views.hgrid.dropbox_addon_folder

# MAX_FILE_SIZE = 5  # MB
