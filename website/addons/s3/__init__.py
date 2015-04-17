import os

from . import model
from . import routes
from . import views

MODELS = [model.AddonS3UserSettings, model.AddonS3NodeSettings, model.S3GuidFile]
USER_SETTINGS_MODEL = model.AddonS3UserSettings
NODE_SETTINGS_MODEL = model.AddonS3NodeSettings

ROUTES = [routes.settings_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon S3'


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
GET_HGRID_DATA = views.hgrid.s3_hgrid_data
# 1024 ** 1024  # There really shouldnt be a limit...
MAX_FILE_SIZE = 128  # MB

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 's3_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 's3_user_settings.mako')
