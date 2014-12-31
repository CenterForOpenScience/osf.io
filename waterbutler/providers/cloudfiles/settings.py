try:
    from waterbutler.settings import CLOUDFILES_PROVIDER_CONFIG
except ImportError:
    CLOUDFILES_PROVIDER_CONFIG = None

config = CLOUDFILES_PROVIDER_CONFIG or {}


TEMP_URL_SECS = config.get('TEMP_URL_SECS', 100)
AUTH_URL = config.get('AUTH_URL', 'https://identity.api.rackspacecloud.com/v2.0/tokens')
