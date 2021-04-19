# Use API settings.
from api.base.settings import *  # noqa: F401,F403


PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
