from . import routes

ROUTES = [routes.api_routes]

SHORT_NAME = 'mendeley'
FULL_NAME = 'Mendeley'

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

WIDGET_HELP = 'Mendeley'

HAS_HGRID_FILES = False

# HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # use default nodes settings templates
USER_SETTINGS_TEMPLATE = None  # use default user settings templates
