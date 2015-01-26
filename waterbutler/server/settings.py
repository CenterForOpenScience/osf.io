import hashlib

try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('SERVER_CONFIG', {})


ADDRESS = config.get('ADDRESS', '127.0.0.1')
PORT = config.get('PORT', 7777)
DEBUG = config.get('DEBUG', True)
XHEADERS = config.get('XHEADERS', False)
CORS_ALLOW_ORIGIN = config.get('CORS_ALLOW_ORIGIN', 'http://localhost:5000')

CHUNK_SIZE = config.get('CHUNK_SIZE', 65536)  # 64KB
MAX_BUFFER_SIZE = config.get('MAX_BUFFER_SIZE', 1024 * 1024 * 100)  # 100MB

IDENTITY_METHOD = config.get('IDENTITY_METHOD', 'rest')
IDENTITY_API_URL = config.get('IDENTITY_API_URL', 'http://127.0.0.1:5001/api/v1/files/auth/')

HMAC_ALGORITHM = getattr(hashlib, config.get('HMAC_ALGORITHM', 'sha256'))
HMAC_SECRET = config.get('HMAC_SECRET', None).encode('utf-8')
