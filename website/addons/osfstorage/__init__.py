#!/usr/bin/env python
# encoding: utf-8

from . import routes, views, model

MODELS = [
    model.OsfStorageNode,
    model.OsfStorageGuidFile,
    model.OsfStorageFileVersion,
    model.OsfStorageNodeSettings,
]
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

MAX_FILE_SIZE = 128  # 128 MB
HIGH_MAX_FILE_SIZE = 5 * 1024  # 5 GB
