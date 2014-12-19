from . import routes, views, model

MODELS = [
    model.AddonGitHubUserSettings,
    model.AddonGitHubNodeSettings,
    model.GithubGuidFile,
    model.AddonGitHubOauthSettings,
]
USER_SETTINGS_MODEL = model.AddonGitHubUserSettings
NODE_SETTINGS_MODEL = model.AddonGitHubNodeSettings

ROUTES = [routes.api_routes, routes.settings_routes, routes.page_routes]

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {}

INCLUDE_CSS = {
    'widget': ['github-rubeus.css'],
    'page': ['/static/css/hgrid-base.css'],
    'files': ['github-rubeus.css']
}

WIDGET_HELP = 'GitHub Add-on Alpha'

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.github_hgrid_data

# Note: Even though GitHub supports file sizes over 1 MB, uploads and
# downloads through their API are capped at 1 MB.
MAX_FILE_SIZE = 1
