from . import routes, views, model

MODELS = [
    model.AddonFilesNodeSettings,
    model.NodeFile,
    model.OsfGuidFile,
]
NODE_SETTINGS_MODEL = model.AddonFilesNodeSettings

ROUTES = [
    routes.settings_routes,
    routes.web_routes,
    routes.api_routes
]

SHORT_NAME = 'osffiles'
FULL_NAME = 'OSF Storage'

OWNERS = ['node']

ADDED_DEFAULT = ['node']
ADDED_MANDATORY = ['node']

VIEWS = []
CONFIGS = []

CATEGORIES = ['storage']

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.get_osffiles_hgrid

MAX_FILE_SIZE = 128
