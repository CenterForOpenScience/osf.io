import hashlib

try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('SERVER_CONFIG', {})


ADDRESS = config.get('ADDRESS', '127.0.0.1')
PORT = config.get('PORT', 7777)

DEBUG = config.get('DEBUG', True)

SSL_CERT_FILE = config.get('SSL_CERT_FILE', None)
SSL_KEY_FILE = config.get('SSL_KEY_FILE', None)

XHEADERS = config.get('XHEADERS', False)
CORS_ALLOW_ORIGIN = config.get('CORS_ALLOW_ORIGIN', '*')

CHUNK_SIZE = config.get('CHUNK_SIZE', 65536)  # 64KB
MAX_BUFFER_SIZE = config.get('MAX_BUFFER_SIZE', 1024 * 1024 * 100)  # 100MB

AUTH_HANDLERS = config.get('AUTH_HANDLERS', [
    'viewonly',
    'rest',
])

HMAC_ALGORITHM = getattr(hashlib, config.get('HMAC_ALGORITHM', 'sha256'))
HMAC_SECRET = config.get('HMAC_SECRET', 'changeme').encode('utf-8')
