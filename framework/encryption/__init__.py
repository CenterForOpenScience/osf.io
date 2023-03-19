from website import settings
from osf.utils.cryptography import kdf, encrypt, decrypt

SENSITIVE_DATA_KEY = kdf(
    settings.SENSITIVE_DATA_SECRET.encode('utf-8'),
    settings.SENSITIVE_DATA_SALT.encode('utf-8')
)


def ensure_bytes(value):
    """Helper function to ensure all inputs are encoded to the proper value utf-8 value regardless of input type"""
    if isinstance(value, bytes):
        return value
    return value.encode('utf-8')


def encrypt(value):
    if value:
        value = ensure_bytes(value)
        return encrypt(value, SENSITIVE_DATA_KEY)
    return None


def decrypt(value):
    if value:
        value = ensure_bytes(value)
        return decrypt(value, SENSITIVE_DATA_KEY)
    return None
