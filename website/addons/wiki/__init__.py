from . import model
from . import routes

MODELS = [model.AddonWikiNodeSettings, model.NodeWikiPage]
NODE_SETTINGS_MODEL = model.AddonWikiNodeSettings

ROUTES = [routes.widget_routes, routes.page_routes, routes.api_routes]

SHORT_NAME = 'wiki'
FULL_NAME = 'Wiki'

OWNERS = ['node']

ADDED_DEFAULT = ['node']
ADDED_MANDATORY = []

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
