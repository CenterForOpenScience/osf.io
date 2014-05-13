from . import model
from . import routes

MODELS = [model.BadgesUserSettings, model.BadgesNodeSettings, model.Badge, model.BadgeAssertion]
USER_SETTINGS_MODEL = model.BadgesUserSettings
NODE_SETTINGS_MODEL = model.BadgesNodeSettings

ROUTES = [routes.render_routes, routes.api_urls, routes.guid_urls]

SHORT_NAME = 'badges'
FULL_NAME = 'Badges'

OWNERS = ['node', 'user']

ADDED_DEFAULT = ['node', 'user']
ADDED_MANDATORY = []

VIEWS = ['widget', 'page']
CONFIGS = ['user']

CATEGORIES = ['documentation']

INCLUDE_JS = {
    'widget': ['bake-badges.js', 'badge-popover.js'],
    'page': [],
}

INCLUDE_CSS = {
    'widget': ['badges-widget.css'],
    'page': [],
}
