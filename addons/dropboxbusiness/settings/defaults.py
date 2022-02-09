# OAuth app keys
DROPBOX_BUSINESS_FILEACCESS_KEY = None
DROPBOX_BUSINESS_FILEACCESS_SECRET = None
DROPBOX_BUSINESS_MANAGEMENT_KEY = None
DROPBOX_BUSINESS_MANAGEMENT_SECRET = None

DROPBOX_BUSINESS_AUTH_CSRF_TOKEN = 'dropboxbusiness-auth-csrf-token'

TEAM_FOLDER_NAME_FORMAT = '{title}_GRDM_{guid}'  # available: {title} {guid}
GROUP_NAME_FORMAT = 'GRDM_{guid}'  # available: {title} {guid}

ADMIN_GROUP_NAME = 'GRDM-ADMIN'

USE_PROPERTY_TIMESTAMP = True
PROPERTY_GROUP_NAME = 'GRDM'
PROPERTY_KEY_TIMESTAMP_STATUS = 'timestamp-status'

PROPERTY_KEYS = (PROPERTY_KEY_TIMESTAMP_STATUS,)

PROPERTY_MAX_DATA_SIZE = 1000

PROPERTY_SPLIT_DATA_CONF = {
    'timestamp': {
        'max_size': 5000,
    }
}

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 5 * 1024

EPPN_TO_EMAIL_MAP = {
    # e.g.
    # 'john@idp.example.com': 'john.smith@mail.example.com',
}

EMAIL_TO_EPPN_MAP = dict(
    [(EPPN_TO_EMAIL_MAP[k], k) for k in EPPN_TO_EMAIL_MAP]
)

DEBUG_FILEACCESS_TOKEN = None
DEBUG_MANAGEMENT_TOKEN = None
DEBUG_ADMIN_DBMID = None
