from .model import AddonFilesNodeSettings
from .routes import settings_routes, widget_routes

NODE_SETTINGS_MODEL = AddonFilesNodeSettings

ROUTES = [settings_routes, widget_routes]

SHORT_NAME = 'files'
FULL_NAME = 'Files'

OWNERS = ['node']

ADDED_TO = {
    'node': True,
}

VIEWS = ['widget', 'page']
CONFIGS = []

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
