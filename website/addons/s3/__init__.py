from . import model
from . import routes
from . import views

MODELS = [model.AddonS3UserSettings, model.AddonS3NodeSettings, model.S3GuidFile]
USER_SETTINGS_MODEL = model.AddonS3UserSettings
NODE_SETTINGS_MODEL = model.AddonS3NodeSettings

ROUTES = [routes.settings_routes, routes.nonapi_routes, routes.api_routes]

SHORT_NAME = 's3'
FULL_NAME = 'Amazon Simple Storage Service'


OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['user', 'node']

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
