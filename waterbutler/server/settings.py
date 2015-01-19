import hashlib

try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('SERVER_CONFIG', {})


ADDRESS = config.get('ADDRESS', '127.0.0.1')
PORT = config.get('PORT', 7777)
DEBUG = config.get('DEBUG', True)

CHUNK_SIZE = config.get('CHUNK_SIZE', 65536)  # 64KB

IDENTITY_METHOD = config.get('IDENTITY_METHOD', 'rest')
IDENTITY_API_URL = config.get('IDENTITY_API_URL', 'http://127.0.0.1:5001/api/v1/files/auth/')

HMAC_ALGORITHM = getattr(hashlib, config.get('HMAC_ALGORITHM', 'sha256'))
HMAC_SECRET = config.get('HMAC_SECRET', 'changeme').encode('utf-8')
