import os

from . import routes, views, model

MODELS = [
    model.AddonGitHubUserSettings,
    model.AddonGitHubNodeSettings,
    model.GithubGuidFile,
    model.AddonGitHubOauthSettings,
]
USER_SETTINGS_MODEL = model.AddonGitHubUserSettings
NODE_SETTINGS_MODEL = model.AddonGitHubNodeSettings

ROUTES = [routes.api_routes, routes.settings_routes]

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {}

INCLUDE_CSS = {}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.github_hgrid_data

# Note: Even though GitHub supports file sizes over 1 MB, uploads and
# downloads through their API are capped at 1 MB.
MAX_FILE_SIZE = 100

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'github_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'github_user_settings.mako')
