import os

from . import routes, views, model  # noqa

MODELS = [
    model.FigshareUserSettings,
    model.FigshareNodeSettings,
]
USER_SETTINGS_MODEL = model.FigshareUserSettings
NODE_SETTINGS_MODEL = model.FigshareNodeSettings

ROUTES = [routes.api_routes]

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
GET_HGRID_DATA = views.figshare_root_folder

MAX_FILE_SIZE = 50

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # use default nodes settings templates
USER_SETTINGS_TEMPLATE = None
