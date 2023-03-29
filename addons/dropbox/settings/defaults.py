# OAuth app keys
DROPBOX_KEY = None
DROPBOX_SECRET = None

DROPBOX_AUTH_CSRF_TOKEN = 'dropbox-auth-csrf-token'
DROPBOX_OAUTH_AUTH_ENDPOINT = 'https://www.dropbox.com/oauth2/authorize'
DROPBOX_OAUTH_TOKEN_ENDPOINT = 'https://www.dropbox.com/oauth2/token'
# Token expires in 4 hours, No refresh at least 2 hours to avoid race condition
REFRESH_TIME = 7199  # 2 hours

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = 5 * 1024
