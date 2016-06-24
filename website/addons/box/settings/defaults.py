# OAuth app keys
BOX_KEY = None
BOX_SECRET = None

REFRESH_TIME = 5 * 60  # 5 minutes
EXPIRY_TIME = 60 * 60 * 24 * 60  # 60 days

BOX_OAUTH_TOKEN_ENDPOINT = 'https://www.box.com/api/oauth2/token'
BOX_OAUTH_AUTH_ENDPOINT = 'https://www.box.com/api/oauth2/authorize'
BOX_OAUTH_REVOKE_ENDPOINT = 'https://api.box.com/oauth2/revoke'
