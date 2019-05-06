import jwe

from website import settings

SENSITIVE_DATA_KEY = jwe.kdf(settings.SENSITIVE_DATA_SECRET, settings.SENSITIVE_DATA_SALT)


def ensure_bytes(value):
    """Helper function to ensure all inputs are encoded to the proper value utf-8 value regardless of input type"""
    if isinstance(value, bytes):
        return value
    return value.encode('utf-8')


def encrypt(value):
    if value:
        value = ensure_bytes(value)
        return jwe.encrypt(value, SENSITIVE_DATA_KEY)
    return None


def decrypt(value):
    if value:
        value = ensure_bytes(value)
        return jwe.decrypt(value, SENSITIVE_DATA_KEY)
    return None
