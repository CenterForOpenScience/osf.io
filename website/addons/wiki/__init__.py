from .model import AddonWikiNodeSettings
from .routes import settings_routes, widget_routes

MODELS = [AddonWikiNodeSettings]
NODE_SETTINGS_MODEL = AddonWikiNodeSettings

ROUTES = [settings_routes, widget_routes]

SHORT_NAME = 'wiki'
FULL_NAME = 'Wiki'

OWNERS = ['node']

ADDED_TO = {
    'node': True,
}

VIEWS = ['widget', 'page']
CONFIGS = []

CATEGORIES = ['documentation']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
