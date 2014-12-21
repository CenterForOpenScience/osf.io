import hashlib

try:
    from waterbutler.settings import CORE_PROVIDER_CONFIG
except ImportError:
    CORE_PROVIDER_CONFIG = {}

config = CORE_PROVIDER_CONFIG


HMAC_SECRET = config.get('HMAC_SECRET')
HMAC_ALGORITHM = config.get('HMAC_ALGORITHM', hashlib.sha256)
