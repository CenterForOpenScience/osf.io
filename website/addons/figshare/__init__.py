from .model import AddonFigShareNodeSettings
from .routes import settings_routes

NODE_SETTINGS_MODEL = AddonFigShareNodeSettings

ROUTES = [settings_routes]

SHORT_NAME = 'figshare'
FULL_NAME = 'FigShare'

OWNERS = ['node']

ADDED_TO = {
    'node': False,
}

VIEWS = ['widget']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

WIDGET_HELP = 'FigShare Add-on Alpha'
