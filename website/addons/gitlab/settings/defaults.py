# GitLab application credentials
CLIENT_ID = None
CLIENT_SECRET = None

# GitLab access scope
SCOPE = ['api']

# GitLab hook domain
HOOK_DOMAIN = None
HOOK_CONTENT_TYPE = 'json'
HOOK_EVENTS = ['push']  # Only log commits

# OAuth related urls
# TODO: use the gitlab instance configured by user/project
OAUTH_AUTHORIZE_URL = 'https://gitlab.com/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://gitlab.com/oauth/token'

GITLAB_BASE_URL = 'https://gitlab.com'

# Max render size in bytes; no max if None
MAX_RENDER_SIZE = None

CACHE = False
