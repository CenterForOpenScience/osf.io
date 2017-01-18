import os

from .routes import settings_routes

SHORT_NAME = 'twofactor'
FULL_NAME = 'Two-factor Authentication'
WIDGET_HELP = 'Two-Factor Authentication (Alpha)'

ROUTES = [settings_routes, ]

OWNERS = ['user', ]

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = []
CONFIGS = ['user']

CATEGORIES = ['security']

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # no node settings view
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'twofactor_user_settings.mako')
