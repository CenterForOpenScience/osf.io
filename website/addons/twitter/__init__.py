from .model import AddonTwitterNodeSettings

from .routes import page_routes

NODE_SETTINGS_MODEL = AddonTwitterNodeSettings
MODELS = [AddonTwitterNodeSettings, ]



ROUTES = [page_routes]

SHORT_NAME = 'twitter'
FULL_NAME = 'Twitter'
OWNERS = ['node']

ADDED_DEFAULT = []
ADDED_MANDATORY=[]

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = ['widget']

CONFIGS = ['node']

CATEGORIES = ['feed']

WIDGET_HELP = 'Twitter Add-on Alpha'
