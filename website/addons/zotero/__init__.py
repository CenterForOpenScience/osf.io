from . import model

MODELS = [
    model.AddonZoteroUserSettings,
]


USER_SETTINGS_MODEL = model.AddonZoteroUserSettings
# NODE_SETTINGS_MODEL = model.AddonGitHubNodeSettings

ROUTES = []

SHORT_NAME = 'zotero'
FULL_NAME = 'Zotero'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

CATEGORIES = ['citations']

INCLUDE_JS = {}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
    'files': []
}

WIDGET_HELP = 'Zotero'

HAS_HGRID_FILES = False
