from .model.settings import AddonFilesSettings
from .routes import settings_routes, widget_routes

SETTINGS_MODEL = AddonFilesSettings

ROUTES = [settings_routes, widget_routes]

SHORT_NAME = 'files'
FULL_NAME = 'Files'

ADDED_BY_DEFAULT = True

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

HAS_PAGE = True