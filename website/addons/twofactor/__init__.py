SHORT_NAME = 'twofactor'
FULL_NAME = 'Two-factor Authentication'
WIDGET_HELP = 'Two-Factor Authentication (Alpha)'

from .models import TwoFactorUserSettings
from .routes import settings_routes

USER_SETTINGS_MODEL = TwoFactorUserSettings

MODELS = [TwoFactorUserSettings]

ROUTES = [settings_routes, ]

OWNERS = ['user', ]

ADDED_TO = {
    'user': False,
    'node': False,
}

VIEWS = []
CONFIGS = ['user']

CATEGORIES = ['security']