# Use API settings.
from api.base.settings import *  # noqa

DEBUG_PROPAGATE_EXCEPTIONS = True
#DATABASES = {
#    'default': {
#        'CONN_MAX_AGE': 0,
#        'ENGINE': 'osf.db.backends.postgresql',
#        'HOST': '',
#        'NAME': 'osf-models-test',
#        'PASSWORD': '',
#        'PORT': '',
#        'USER': '',
#        'ATOMIC_REQUESTS': True,
#    }
#}
SITE_ID = 1
# SECRET_KEY = 'not very secret in tests'
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
