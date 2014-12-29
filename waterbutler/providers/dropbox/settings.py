try:
    from waterbutler.settings import DROPBOX_PROVIDER_CONFIG
except ImportError:
    DROPBOX_PROVIDER_CONFIG = {}

config = DROPBOX_PROVIDER_CONFIG


BASE_URL = config.get('BASE_URL', 'https://api.dropbox.com/1/')
BASE_CONTENT_URL = config.get('BASE_CONTENT_URL', 'https://api-content.dropbox.com/1/')
