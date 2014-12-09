#!/usr/bin/env python
# encoding: utf-8

from . import routes, views, model

MODELS = [
    model.OsfStorageNodeSettings,
    model.OsfStorageFileTree,
    model.OsfStorageFileRecord,
    model.OsfStorageFileVersion,
    model.OsfStorageGuidFile,
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
    'files': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views.osf_storage_root

MAX_FILE_SIZE = 128
