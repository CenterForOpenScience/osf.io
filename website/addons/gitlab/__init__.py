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

SHORT_NAME = 'gitlab'
FULL_NAME = 'GitLab'

OWNERS = ['user', 'node']

ADDED_DEFAULT = ['user', 'node']
ADDED_MANDATORY = ['user', 'node']

VIEWS = []
CONFIGS = []

CATEGORIES = ['storage']

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.get_osffiles_hgrid

MAX_FILE_SIZE = 1024 * 1024 * 128
