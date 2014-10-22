from . import model
from . import routes

MODELS = [
    model.Metadata,
    model.AppNodeSettings,
]

NODE_SETTINGS_MODEL = model.AppNodeSettings

ROUTES = [routes.api_routes, routes.web_routes, routes.metadata_routes, routes.custom_routing_routes]

SHORT_NAME = 'app'
FULL_NAME = 'Application'

OWNERS = ['node']

VIEWS = ['page']
CONFIGS = ['node']

CATEGORIES = ['service']

INCLUDE_JS = {
    'page': [],
    'files': []
}

INCLUDE_CSS = {
    'page': [],
    'files': []
}

HAS_HGRID_FILES = False
