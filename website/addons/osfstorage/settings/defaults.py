# encoding: utf-8

import os

from website import settings


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

DISK_SAVING_MODE = settings.DISK_SAVING_MODE
