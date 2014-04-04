import os
from website.settings import BASE_PATH, DOMAIN


HOST = None
TOKEN = None

ROOT_NAME = None
ROOT_PASS = None

PROJECTS_LIMIT = 999999

ACCESS_LEVELS = {
    'admin': 'master',
    'write': 'developer',
    'read': 'reporter',
}

DEFAULT_BRANCH = 'master'

HOOK_DOMAIN = DOMAIN

MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}

TMP_DIR = os.path.join(BASE_PATH, 'gitlab')
