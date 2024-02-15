import importlib
import os
import logging
from website import settings


logger = logging.getLogger(__name__)

DEFAULT_REGION_NAME = 'United States'
DEFAULT_REGION_ID = 'us'

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
    mod = importlib.import_module(f'.{settings.MIGRATION_ENV}', package='addons.osfstorage.settings')
    globals().update({k: getattr(mod, k) for k in dir(mod)})
except Exception as ex:
    logger.warning(f'No migration settings loaded for OSFStorage, falling back to local dev. {ex}')

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 5 * 1024  # 5 GB

# Max file size permitted by frontend in megabytes for verified users
HIGH_MAX_UPLOAD_SIZE = 5 * 1024  # 5 GB
