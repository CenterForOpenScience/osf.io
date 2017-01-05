# Use API defaults. This allows these settings to work with API tests
from api.base.settings.defaults import *  # noqa

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

REST_FRAMEWORK['ALLOWED_VERSIONS'] = (
        '2.0',
        '2.0.1',
        '2.1',
        '2.2',
        '2.3',
        '3.0',
        '3.0.1',
    )
