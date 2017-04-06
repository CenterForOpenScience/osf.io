# OAuth app keys
BOX_KEY = None
BOX_SECRET = None

# https://docs.box.com/docs/oauth-20#section-6-using-the-access-and-refresh-tokens
EXPIRY_TIME = 60 * 60 * 24 * 60  # 60 days
REFRESH_TIME = 5 * 60  # 5 minutes

BOX_OAUTH_TOKEN_ENDPOINT = 'https://www.box.com/api/oauth2/token'
BOX_OAUTH_AUTH_ENDPOINT = 'https://www.box.com/api/oauth2/authorize'
BOX_OAUTH_REVOKE_ENDPOINT = 'https://api.box.com/oauth2/revoke'
