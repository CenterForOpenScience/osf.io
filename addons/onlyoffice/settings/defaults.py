from website import settings as osf_settings

# SECURITY WARNING: don't run with debug turned on in production!
DEV_MODE = osf_settings.DEV_MODE
DEBUG = osf_settings.DEBUG_MODE

OFFICESERVER_JWE_SALT = 'xxxxx'
OFFICESERVER_JWE_SECRET = 'yyyyy'
OFFICESERVER_JWT_SECRET = 'zzzzz'
OFFICESERVER_JWT_ALGORITHM = 'HS256'


# WOPI settings.
# Session timer (seconds). Default is 10 hour.
WOPI_TOKEN_TTL = 10 * 60 * 60

# Difference between access_token_ttl and expiration timer encrypted in access_token. (seconds)
# Default is 60 sec.
WOPI_EXPIRATION_TIMER_DELAY = 60

# WOPI_CLIENT_ONLYOFFICE is ONLYOFFICE online editor's host and port FROM web server.
WOPI_CLIENT_ONLYOFFICE = None

# WOPI_SRC_HOST is web server's host and port which can access FROM WOPI CLIENT.
WOPI_SRC_HOST = None
