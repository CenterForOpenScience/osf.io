import os
import json
from website.settings import BASE_PATH, DOMAIN


HOST = None
TOKEN = None

# Only used in migration scripts
ROOT_NAME = None
ROOT_PASS = None

PROJECTS_LIMIT = 999999

ACCESS_LEVELS = {
    'admin': 'master',
    'write': 'developer',
    'read': 'reporter',
}

DEFAULT_BRANCH = 'master'

# `HOOK_DOMAIN` defaults to `DOMAIN`, which should be the value used in
# production. This can be changed in local.py for use with services like
# ngrok or localtunnel.
HOOK_DOMAIN = DOMAIN

MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}

# Load routing table for download URLs if available
try:
    compat_file = os.path.join(BASE_PATH, 'compat_file_routes.json')
    COMPAT_ROUTES = json.load(open(compat_file))
except IOError:
    COMPAT_ROUTES = {}
