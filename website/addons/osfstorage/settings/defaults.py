# encoding: utf-8

import os
import datetime

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

DEFAULT_STORAGE_LIMIT = (1024 ** 3) * 2  # 2GB
WARNING_EMAIL_THRESHOLD = (1024 ** 3) * 0.5  # .5GB
WARNING_EMAIL_WAITING_PERIOD = datetime.timedelta(weeks=1)
DISK_SAVING_MODE = settings.DISK_SAVING_MODE
