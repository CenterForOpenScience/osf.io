import os

from . import model
from . import routes
from . import views

MODELS = [model.AddonShareLatexUserSettings, model.AddonShareLatexNodeSettings]
USER_SETTINGS_MODEL = model.AddonShareLatexUserSettings
NODE_SETTINGS_MODEL = model.AddonShareLatexNodeSettings

ROUTES = [routes.settings_routes]

SHORT_NAME = 'sharelatex'
FULL_NAME = 'ShareLatex'


OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.hgrid.sharelatex_hgrid_data
# 1024 ** 1024  # There really shouldnt be a limit...
MAX_FILE_SIZE = 128  # MB

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'sharelatex_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'sharelatex_user_settings.mako')
