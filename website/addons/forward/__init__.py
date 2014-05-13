from website.addons.forward import model, routes, views


MODELS = [model.ForwardNodeSettings]
NODE_SETTINGS_MODEL = model.ForwardNodeSettings

ROUTES = [routes.api_routes]

SHORT_NAME = 'forward'
FULL_NAME = 'Forward'

OWNERS = ['node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget']
CONFIGS = ['node']

CATEGORIES = ['other']

INCLUDE_JS = {
    'page': [],
    'files': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
