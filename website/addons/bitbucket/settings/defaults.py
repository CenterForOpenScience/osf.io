# Bitbucket application credentials
CLIENT_ID = None
CLIENT_SECRET = None

# Bitbucket access scope
SCOPE = ['account', 'repository', 'team']

# Bitbucket hook domain
HOOK_DOMAIN = None
HOOK_CONTENT_TYPE = 'json'
HOOK_EVENTS = ['push']  # Only log commits

# OAuth related urls
OAUTH_AUTHORIZE_URL = 'https://bitbucket.org/site/oauth2/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://bitbucket.org/site/oauth2/access_token'

# Max render size in bytes; no max if None
MAX_RENDER_SIZE = None

CACHE = False

BITBUCKET_V1_API_URL = 'https://api.bitbucket.org/1.0'
BITBUCKET_V2_API_URL = 'https://api.bitbucket.org/2.0'

REFRESH_TIME = 5 * 60
EXPIRY_TIME = 0
