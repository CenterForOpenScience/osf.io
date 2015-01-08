import hashlib

try:
    from waterbutler.settings import SERVER_CONFIG
except ImportError:
    SERVER_CONFIG = None

config = SERVER_CONFIG or {}


ADDRESS = config.get('ADDRESS', '0.0.0.0')
PORT = config.get('PORT', 7777)
DEBUG = config.get('DEBUG', True)

CHUNK_SIZE = config.get('CHUNK_SIZE', 65536)  # 64KB

IDENTITY_METHOD = config.get('IDENTITY_METHOD', 'rest')
IDENTITY_API_URL = config.get('IDENTITY_API_URL', 'http://127.0.0.1:5000/api/v1/files/auth/')

HMAC_ALGORITHM = hashlib.sha256
HMAC_SECRET = config.get('HMAC_SECRET', 'changeme').encode('utf-8')
