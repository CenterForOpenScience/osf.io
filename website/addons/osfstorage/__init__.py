#!/usr/bin/env python
# encoding: utf-8

from . import routes, views, model
from . import listeners  # noqa

MODELS = [model.OsfStorageNodeSettings]
NODE_SETTINGS_MODEL = model.OsfStorageNodeSettings

ROUTES = [
    routes.api_routes
]

SHORT_NAME = 'osfstorage'
FULL_NAME = 'OSF Storage'

OWNERS = ['node']

ADDED_DEFAULT = ['node']
ADDED_MANDATORY = ['node']

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

MAX_FILE_SIZE = 5 * 1024  # 5 GB
HIGH_MAX_FILE_SIZE = 5 * 1024  # 5 GB

# HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = None  # no node settings view
USER_SETTINGS_TEMPLATE = None  # no user settings view
