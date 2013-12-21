from .model.settings import AddonWikiSettings
from .routes import settings_routes

SETTINGS_MODEL = AddonWikiSettings

ROUTES = [settings_routes]

SHORT_NAME = 'wiki'
FULL_NAME = 'Wiki'

ADDED_BY_DEFAULT = True

CATEGORIES = ['documentation']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}
