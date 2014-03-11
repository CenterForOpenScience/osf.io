HOST = None
TOKEN = None

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
