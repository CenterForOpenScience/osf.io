from .model import TwoFactorUserSettings

SHORT_NAME = 'twofactor'
FULL_NAME = 'Two-factor Authentication'
WIDGET_HELP = 'Two-Factor Authentication (Alpha)'

USER_SETTINGS_MODEL = TwoFactorUserSettings

MODELS = [TwoFactorUserSettings]
OWNERS = ['user', ]
CATEGORIES = ['security']
