try:
    from waterbutler.settings import SERVER_CONFIG
except ImportError:
    SERVER_CONFIG = {}

config = SERVER_CONFIG


ADDRESS = config.get('ADDRESS', '127.0.0.1')
PORT = config.get('PORT', 7777)
DEBUG = config.get('DEBUG', True)

CHUNK_SIZE = config.get('CHUNK_SIZE', 65536)  # 64KB

IDENTITY_METHOD = config.get('IDENTITY_METHOD', 'rest')
IDENTITY_API_URL = config.get('IDENTITY_API_URL', 'changeme')
