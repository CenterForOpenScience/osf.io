# encoding: utf-8
import importlib
import os
import logging
from website import settings


logger = logging.getLogger(__name__)

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


try:
    importlib.import_module('.{}'.format(settings.MIGRATION_ENV))
except:
    logger.warn('No migration settings loaded for OSFStorage, falling back to local dev.')
