try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('OSF_AUTH_CONFIG', {})

API_URL = config.get('API_URL', 'http://127.0.0.1:5000/api/v1/files/auth/')
