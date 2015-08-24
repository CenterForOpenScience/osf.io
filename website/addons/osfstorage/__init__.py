import os

from . import routes, views, model, oldels

MODELS = [
    oldels.OsfStorageFileTree,
    oldels.OsfStorageFileRecord,
    model.OsfStorageFileNode,
    model.OsfStorageGuidFile,
    model.OsfStorageFileVersion,
    model.OsfStorageNodeSettings,
    model.OsfStorageUserSettings,
    model.OsfStorageTrashedFileNode,
]
NODE_SETTINGS_MODEL = model.OsfStorageNodeSettings
USER_SETTINGS_MODEL = model.OsfStorageUserSettings

ROUTES = [
    routes.api_routes
]

SHORT_NAME = 'osfstorage'
FULL_NAME = 'OSF Storage'

OWNERS = ['node', 'user']

ADDED_DEFAULT = ['node', 'user']
ADDED_MANDATORY = ['node', 'user']

VIEWS = []
CONFIGS = []

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
    'files': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.osf_storage_root

MAX_FILE_SIZE = 128  # 128 MB
HIGH_MAX_FILE_SIZE = 5 * 1024  # 5 GB

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # no node settings view
USER_SETTINGS_TEMPLATE = None  # no user settings view
