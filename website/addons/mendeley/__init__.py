from . import model

MODELS = [
    model.AddonMendeleyUserSettings,
]


USER_SETTINGS_MODEL = model.AddonMendeleyUserSettings
# NODE_SETTINGS_MODEL = model.AddonGitHubNodeSettings

ROUTES = []

SHORT_NAME = 'mendeley'
FULL_NAME = 'Mendeley'

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

WIDGET_HELP = 'Mendeley'

HAS_HGRID_FILES = False
