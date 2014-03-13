HOST = None
TOKEN = None

ROOT_NAME = None
ROOT_PASS = None

ACCESS_LEVELS = {
    'admin': 'master',
    'write': 'developer',
    'read': 'reporter',
}

MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}

import os
from website.settings import BASE_PATH
TMP_DIR = os.path.join(BASE_PATH, 'gitlab')
