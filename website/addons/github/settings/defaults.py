# GitHub application credentials
CLIENT_ID = None
CLIENT_SECRET = None

# GitHub access scope
SCOPE = ['repo']

# GitHub hook domain
HOOK_DOMAIN = None
HOOK_CONTENT_TYPE = 'json'
HOOK_EVENTS = ['push']  # Only log commits

# OAuth related urls
OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'

# Max render size in bytes; no max if None
MAX_RENDER_SIZE = None

CACHE = False
