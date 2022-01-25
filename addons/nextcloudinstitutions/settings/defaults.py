DEFAULT_HOSTS = []
USE_SSL = True

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 5 * 1024

DEFAULT_BASE_FOLDER = '/GRDM'

# available: {title} {guid}
ROOT_FOLDER_FORMAT = 'GRDM_{title}_{guid}'

PROPERTY_KEY_TIMESTAMP = 'grdm-timestamp'
PROPERTY_KEY_TIMESTAMP_STATUS = 'grdm-timestamp-status'

DEBUG_URL = None
DEBUG_USER = None
DEBUG_PASSWORD = None

# OSFUser GUID to NextCloud User
# DEBUG_USERMAP = {
#  'abcde': 'user01',
#  'fg123': 'user02',
#}
DEBUG_USERMAP = None
