try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('BOX_PROVIDER_CONFIG', {})


BASE_URL = config.get('BASE_URL', 'https://view-api.box.com/1')
BASE_CONTENT_URL = config.get('BASE_CONTENT_URL', 'https://api.box.com/2.0')
