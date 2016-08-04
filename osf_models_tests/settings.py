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
STATIC_URL = '/static/'
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'osf_models',
)
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
