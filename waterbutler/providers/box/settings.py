try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('BOX_PROVIDER_CONFIG', {})


BASE_URL = config.get('BASE_URL', 'https://api.box.com/2.0')
BASE_UPLOAD_URL = config.get('BASE_CONTENT_URL', 'https://upload.box.com/api/2.0')
