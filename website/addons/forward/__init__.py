import os

from website.addons.forward import model, routes, views  # noqa


MODELS = [model.ForwardNodeSettings]
NODE_SETTINGS_MODEL = model.ForwardNodeSettings

ROUTES = [routes.api_routes]

SHORT_NAME = 'forward'
FULL_NAME = 'External Link'

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

curdir = os.path.dirname(os.path.realpath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(curdir, 'template', 'forward_node_settings.mako')
USER_SETTINGS_TEMPLATE = None  # has no user-facing settings
