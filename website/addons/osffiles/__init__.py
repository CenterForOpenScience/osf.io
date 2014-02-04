from . import routes, views, model

MODELS = [model.AddonFilesNodeSettings, model.NodeFile]
NODE_SETTINGS_MODEL = model.AddonFilesNodeSettings

ROUTES = [
    routes.settings_routes,
    routes.widget_routes,
    routes.web_routes,
    routes.api_routes
]

SHORT_NAME = 'osffiles'
FULL_NAME = 'OSF Files'

OWNERS = ['node']

ADDED_TO = {
    'node': True,
}

VIEWS = []
CONFIGS = []

CATEGORIES = ['storage']

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.osffiles_dummy_folder

MAX_FILE_SIZE = 1024 * 1024 * 128
