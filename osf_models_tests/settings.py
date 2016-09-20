# Use API defaults. This allows these settings to work with API tests
from api.base.settings.defaults import *  # noqa
DEBUG_PROPAGATE_EXCEPTIONS = True
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 0,
        'ENGINE': 'osf_models.db.backends.postgresql',
        'HOST': '',
        'NAME': 'osf-models-test',
        'PASSWORD': '',
        'PORT': '',
        'USER': '',
    }
}
SITE_ID = 1
SECRET_KEY = 'not very secret in tests'
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
