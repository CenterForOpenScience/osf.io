try:
    from waterbutler.settings import OSFSTORAGE_PROVIDER_CONFIG
except ImportError:
    OSFSTORAGE_PROVIDER_CONFIG = {}

config = OSFSTORAGE_PROVIDER_CONFIG


import hashlib


FILE_PATH_PENDING = config.get('FILE_PATH_PENDING', '/tmp/pending')
FILE_PATH_COMPLETE = config.get('FILE_PATH_COMPLETE', '/tmp/complete')

BROKER_URL = config.get('BROKER_URL', 'amqp://')
CELERY_RESULT_BACKEND = config.get('CELERY_RESULT_BACKEND', 'redis://')
CELERY_IMPORTS = config.get('CELERY_IMPORTS', (
    'waterbutler.tasks.parity',
    'waterbutler.tasks.backup',
))
CELERY_DISABLE_RATE_LIMITS = config.get('CELERY_DISABLE_RATE_LIMITS', True)
CELERY_TASK_RESULT_EXPIRES = config.get('CELERY_TASK_RESULT_EXPIRES', 60)
# CELERY_ALWAYS_EAGER = config.get('CELERY_ALWAYS_EAGER', True)

# Retry options
UPLOAD_RETRY_ATTEMPTS = config.get('UPLOAD_RETRY_ATTEMPTS', 1)
UPLOAD_RETRY_INIT_DELAY = config.get('UPLOAD_RETRY_INIT_DELAY', 30)
UPLOAD_RETRY_MAX_DELAY = config.get('UPLOAD_RETRY_MAX_DELAY', 60 * 60)
UPLOAD_RETRY_BACKOFF = config.get('UPLOAD_RETRY_BACKOFF', 2)
UPLOAD_RETRY_WARN_IDX = config.get('UPLOAD_RETRY_WARN_IDX', 5)

HOOK_RETRY_ATTEMPTS = config.get('HOOK_RETRY_ATTEMPTS ', 1)
HOOK_RETRY_INIT_DELAY = config.get('HOOK_RETRY_INIT_DELAY', 30)
HOOK_RETRY_MAX_DELAY = config.get('HOOK_RETRY_MAX_DELAY', 60 * 60)
HOOK_RETRY_BACKOFF = config.get('HOOK_RETRY_BACKOFF', 2)
HOOK_RETRY_WARN_IDX = config.get('HOOK_RETRY_WARN_IDX', None)

PARITY_RETRY_ATTEMPTS = config.get('PARITY_RETRY_ATTEMPTS', 1)
PARITY_RETRY_INIT_DELAY = config.get('PARITY_RETRY_INIT_DELAY', 30)
PARITY_RETRY_MAX_DELAY = config.get('PARITY_RETRY_MAX_DELAY', 60 * 60)
PARITY_RETRY_BACKOFF = config.get('PARITY_RETRY_BACKOFF', 2)
PARITY_RETRY_WARN_IDX = config.get('PARITY_RETRY_WARN_IDX', None)

# Parity options
RUN_PARITY = config.get('RUN_PARITY', False)
PARITY_CONTAINER_NAME = config.get('PARITY_CONTAINER_NAME', None)
PARITY_REDUNDANCY = config.get('PARITY_REDUNDANCY', 5)
PARITY_PROVIDER_NAME = config.get('PARITY_PROVIDER_NAME', 'cloudfiles')
PARITY_PROVIDER_CREDENTIALS = config.get('PARITY_PROVIDER_CREDENTIALS', {})
PARITY_PROVIDER_SETTINGS = config.get('PARITY_PROVIDER_SETTINGS', {})

# Backup options
# TODO: rename keys to 'backup_' and generalize with dynamic provider
AWS_ACCESS_KEY = config.get('AWS_ACCESS_KEY', 'changeme')
AWS_SECRET_KEY = config.get('AWS_SECRET_KEY', 'changeme')
GLACIER_VAULT = config.get('GLACIER_VAULT', 'changeme')

# HMAC options
HMAC_SECRET = config.get('HMAC_SECRET', b'changeme')
HMAC_ALGORITHM = config.get('HMAC_ALGORITHM', hashlib.sha256)
