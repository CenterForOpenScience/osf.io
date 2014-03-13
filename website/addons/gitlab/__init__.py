from . import routes, views, model

MODELS = [
    model.AddonGitlabUserSettings,
    model.AddonGitlabNodeSettings,
    model.GitlabGuidFile,
]
USER_SETTINGS_MODEL = model.AddonGitlabUserSettings
NODE_SETTINGS_MODEL = model.AddonGitlabNodeSettings

ROUTES = [
    routes.api_routes,
    routes.page_routes,
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
GET_HGRID_DATA = views.crud.gitlib_hgrid_root

MAX_FILE_SIZE = 32
