from .model import AddonLinkNodeSettings
from .routes import settings_routes, page_routes

NODE_SETTINGS_MODEL = AddonLinkNodeSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'link'
FULL_NAME = 'External Link'

OWNERS = ['node']

ADDED_TO = {
    'node': False,
}

VIEWS = ['widget', 'page']
CONFIGS = ['node']

CATEGORIES = ['other']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

WIDGET_HELP = 'External Link Add-on'
