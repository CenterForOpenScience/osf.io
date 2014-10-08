# -*- coding: utf-8 -*-

from . import routes, views, model

MODELS = [
    model.OsfStorageNodeSettings,
    model.FileTree,
    model.FileRecord,
    model.FileVersion,
    model.StorageFile,
]
NODE_SETTINGS_MODEL = model.OsfStorageNodeSettings

ROUTES = [
    routes.web_routes,
    routes.api_routes,
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
    'files': ['storageRubeusConfig.js'],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.osf_storage_root

