from . import routes

ROUTES = [routes.api_routes]

SHORT_NAME = 'zotero'
FULL_NAME = 'Zotero'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget']
CONFIGS = ['accounts', 'node']

CATEGORIES = ['citations']

INCLUDE_JS = {}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
    'files': []
}

WIDGET_HELP = 'Zotero'

HAS_HGRID_FILES = False

NODE_SETTINGS_TEMPLATE = None  # use default node settings template
USER_SETTINGS_TEMPLATE = None  # use default user settings template
