# GitHub application credentials
CLIENT_ID = '991208e6442787ff6870'
CLIENT_SECRET = 'b57c5ccc87489b90dd5c57233d7d29315487a39d'

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
