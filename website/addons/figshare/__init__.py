import os

from . import routes, views, model  # noqa

MODELS = [
    model.AddonFigShareUserSettings,
    model.AddonFigShareNodeSettings,
]
USER_SETTINGS_MODEL = model.AddonFigShareUserSettings
NODE_SETTINGS_MODEL = model.AddonFigShareNodeSettings

ROUTES = [routes.settings_routes, routes.api_routes]

SHORT_NAME = 'figshare'
FULL_NAME = 'figshare'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {}
INCLUDE_CSS = {}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.figshare_hgrid_data

MAX_FILE_SIZE = 50

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # use default nodes settings templates
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'figshare_user_settings.mako')
