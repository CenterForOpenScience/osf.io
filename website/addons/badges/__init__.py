import os

from website.settings import BASE_PATH

from . import model
from . import routes

MODELS = [model.BadgesNodeSettings, model.BadgesUserSettings, model.Badge, model.BadgeAssertion]
NODE_SETTINGS_MODEL = model.BadgesNodeSettings
USER_SETTINGS_MODEL = model.BadgesUserSettings

ROUTES = [routes.widget_route, routes.api_urls, routes.guid_urls]

BADGES_LOCATION = os.path.join(BASE_PATH, 'badges')

SHORT_NAME = 'badges'
FULL_NAME = 'Badges'

OWNERS = ['node', 'user']

ADDED_DEFAULT = ['node', 'user']
ADDED_MANDATORY = []

VIEWS = ['widget']
CONFIGS = ['user']

CATEGORIES = ['documentation']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
