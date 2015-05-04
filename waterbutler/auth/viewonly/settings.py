try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('VIEWONLY_AUTH_CONFIG', {})

API_URL = config.get('API_URL', 'http://127.0.0.1:5001/api/v1/files/auth/')
URL_PARAMETER_NAME = config.get('URL_PARAMETER_NAME', 'view_only')
