# OAuth app keys
DROPBOX_BUSINESS_FILE_KEY = None
DROPBOX_BUSINESS_FILE_SECRET = None
DROPBOX_BUSINESS_MANAGEMENT_KEY = None
DROPBOX_BUSINESS_MANAGEMENT_SECRET = None

DROPBOX_BUSINESS_AUTH_CSRF_TOKEN = 'dropboxbusiness-auth-csrf-token'

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 150

EPPN_TO_EMAIL_MAP = {
    # e.g.
    # 'john@openidp.example.com': 'john.smith@mail.example.com',
}

EMAIL_TO_EPPN_MAP = dict(
    [(EPPN_TO_EMAIL_MAP[k], k) for k in EPPN_TO_EMAIL_MAP]
)

DEBUG_FILE_ACCESS_TOKEN = None
DEBUG_MANAGEMENT_ACCESS_TOKEN = None
DEBUG_ADMIN_DBMID = None
