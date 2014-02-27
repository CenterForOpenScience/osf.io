from .model import AddonZoteroNodeSettings
from .routes import settings_routes, page_routes, widget_routes

MODELS = [AddonZoteroNodeSettings]
NODE_SETTINGS_MODEL = AddonZoteroNodeSettings

ROUTES = [settings_routes, page_routes, widget_routes]

SHORT_NAME = 'zotero'
FULL_NAME = 'Zotero'

OWNERS = ['node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget', 'page']
CONFIGS = ['node']

CATEGORIES = ['bibliography']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

WIDGET_HELP = 'Zotero Add-on Alpha'
