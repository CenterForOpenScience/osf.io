from . import routes, views, model

MODELS = [
    model.AddonGitlabUserSettings,
    model.AddonGitlabUserSettings,
    model.GitlabGuidFile,
]
USER_SETTINGS_MODEL = model.AddonGitlabUserSettings
NODE_SETTINGS_MODEL = model.AddonGitlabNodeSettings

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
GET_HGRID_DATA = views.crud.gitlab_list_files

MAX_FILE_SIZE = 32
