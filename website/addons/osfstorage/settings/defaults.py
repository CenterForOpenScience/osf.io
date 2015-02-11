# encoding: utf-8

import os

from website import settings


REVISIONS_PAGE_SIZE = 10

WATERBUTLER_CREDENTIALS = {
    'storage': {}
}

WATERBUTLER_SETTINGS = {
    'storage': {
        'provider': 'filesystem',
        'folder': os.path.join(settings.BASE_PATH, 'osfstoragecache'),
    }
}

WATERBUTLER_RESOURCE = 'folder'