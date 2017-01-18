import os
from . import routes, views  # noqa

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

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'forward_node_settings.mako')
USER_SETTINGS_TEMPLATE = None  # has no user-facing settings
