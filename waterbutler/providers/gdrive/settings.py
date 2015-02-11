try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('GOOGLEDRIVE_PROVIDER_CONFIG', {})


BASE_URL = config.get('BASE_URL', 'https://www.googleapis.com/drive/v2')
BASE_CONTENT_URL = config.get('BASE_CONTENT_URL', 'https://www.googleapis.com/upload/drive/v2')
