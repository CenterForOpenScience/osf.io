"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 1.8.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os
from future.moves.urllib.parse import urlparse
from website import settings as osf_settings
from corsheaders.defaults import default_headers

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

DATABASES = {
    'default': {
        'CONN_MAX_AGE': 0,
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('OSF_DB_NAME', 'osf'),
        'USER': os.environ.get('OSF_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('OSF_DB_PASSWORD', ''),
        'HOST': os.environ.get('OSF_DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('OSF_DB_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
        'TEST': {
            'SERIALIZE': False,
        },
    },
}

DATABASE_ROUTERS = ['osf.db.router.PostgreSQLFailoverRouter', ]
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

AUTH_USER_MODEL = 'osf.OSFUser'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = osf_settings.SECRET_KEY

AUTHENTICATION_BACKENDS = (
    'api.base.authentication.backends.ODMBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEV_MODE = osf_settings.DEV_MODE
DEBUG = osf_settings.DEBUG_MODE
DEBUG_PROPAGATE_EXCEPTIONS = True

# session:
SESSION_COOKIE_NAME = 'api'
SESSION_COOKIE_SECURE = osf_settings.SECURE_MODE
SESSION_COOKIE_HTTPONLY = osf_settings.SESSION_COOKIE_HTTPONLY
SESSION_COOKIE_SAMESITE = osf_settings.SESSION_COOKIE_SAMESITE

# csrf:
CSRF_COOKIE_NAME = 'api-csrf'
CSRF_COOKIE_SECURE = osf_settings.SECURE_MODE
CSRF_COOKIE_HTTPONLY = osf_settings.SECURE_MODE

ALLOWED_HOSTS = [
    '.osf.io',
]


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # 3rd party
    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'corsheaders',
    'raven.contrib.django.raven_compat',
    'django_extensions',
    'guardian',
    'storages',
    'waffle',
    'elasticsearch_metrics',

    # OSF
    'osf',

    # Addons
    'addons.osfstorage',
    'addons.bitbucket',
    'addons.box',
    'addons.dataverse',
    'addons.dropbox',
    'addons.figshare',
    'addons.forward',
    'addons.github',
    'addons.gitlab',
    'addons.googledrive',
    'addons.mendeley',
    'addons.onedrive',
    'addons.owncloud',
    'addons.s3',
    'addons.twofactor',
    'addons.wiki',
    'addons.zotero',
)

# local development using https
if osf_settings.SECURE_MODE and DEBUG:
    INSTALLED_APPS += ('sslserver',)

# TODO: Are there more granular ways to configure reporting specifically related to the API?
RAVEN_CONFIG = {
    'tags': {'App': 'api'},
    'dsn': osf_settings.SENTRY_DSN,
    'release': osf_settings.VERSION,
}

BULK_SETTINGS = {
    'DEFAULT_BULK_LIMIT': 100,
}

MAX_PAGE_SIZE = 100

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'DEFAULT_RENDERER_CLASSES': (
        'api.base.renderers.JSONAPIRenderer',
        'api.base.renderers.JSONRendererWithESISupport',
        'api.base.renderers.BrowsableAPIRendererNoForms',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'api.base.parsers.JSONAPIParser',
        'api.base.parsers.JSONAPIParserForRegularJSON',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'EXCEPTION_HANDLER': 'api.base.exceptions.json_api_exception_handler',
    'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'api.base.content_negotiation.JSONAPIContentNegotiation',
    'DEFAULT_VERSIONING_CLASS': 'api.base.versioning.BaseVersioning',
    'DEFAULT_VERSION': '2.0',
    'ALLOWED_VERSIONS': (
        '2.0',
        '2.1',
        '2.2',
        '2.3',
        '2.4',
        '2.5',
        '2.6',
        '2.7',
        '2.8',
        '2.9',
        '2.10',
        '2.11',
        '2.12',
        '2.13',
        '2.14',
        '2.15',
        '2.16',
        '2.17',
        '2.18',
        '2.19',
        '2.20',
    ),
    'DEFAULT_FILTER_BACKENDS': ('api.base.filters.OSFOrderingFilter',),
    'DEFAULT_PAGINATION_CLASS': 'api.base.pagination.JSONAPIPagination',
    'ORDERING_PARAM': 'sort',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Custom auth classes
        'api.base.authentication.drf.OSFBasicAuthentication',
        'api.base.authentication.drf.OSFSessionAuthentication',
        'api.base.authentication.drf.OSFCASAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
        'api.base.throttling.NonCookieAuthThrottle',
        'api.base.throttling.BurstRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/day',
        'non-cookie-auth': '100/hour',
        'add-contributor': '10/second',
        'create-guid': '1000/hour',
        'root-anon-throttle': '1000/hour',
        'test-user': '2/hour',
        'test-anon': '1/hour',
        'send-email': '2/minute',
        'burst': '10/second',
        'files': '75/minute',
        'files-burst': '3/second',
    },
}

# Settings related to CORS Headers addon: allow API to receive authenticated requests from OSF
# CORS plugin only matches based on "netloc" part of URL, so as workaround we add that to the list
CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = (
    osf_settings.DOMAIN.rstrip('/'),
)
# This needs to remain True to allow cross origin requests that are in CORS_ORIGIN_WHITELIST to
# use cookies.
CORS_ALLOW_CREDENTIALS = True
# Allow 'cache-control' in addition to default request headers
# to enable file upload using dropzone.js
CORS_ALLOW_HEADERS = list(default_headers) + [
    'cache-control',
]
# Set dynamically on app init
ORIGINS_WHITELIST = ()

MIDDLEWARE = (
    'api.base.middleware.DjangoGlobalMiddleware',
    'api.base.middleware.CeleryTaskMiddleware',
    'api.base.middleware.PostcommitTaskMiddleware',
    # A profiling middleware. ONLY FOR DEV USE
    # Uncomment and add "prof" to url params to recieve a profile for that url
    # 'api.base.middleware.ProfileMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'api.base.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'waffle.middleware.WaffleMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


ROOT_URLCONF = 'api.base.urls'
WSGI_APPLICATION = 'api.base.wsgi.application'


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# https://django-storages.readthedocs.io/en/latest/backends/gcloud.html
if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', False):
    # Required to interact with Google Cloud Storage
    DEFAULT_FILE_STORAGE = 'api.base.storage.RequestlessURLGoogleCloudStorage'
    GS_BUCKET_NAME = os.environ.get('GS_BUCKET_NAME', 'cos-osf-stage-cdn-us')
    GS_FILE_OVERWRITE = os.environ.get('GS_FILE_OVERWRITE', False)
elif osf_settings.DEV_MODE or osf_settings.DEBUG_MODE:
    DEFAULT_FILE_STORAGE = 'api.base.storage.DevFileSystemStorage'

# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static/vendor')

API_BASE = 'v2/'
API_PRIVATE_BASE = '_/'
STATIC_URL = '/static/'

NODE_CATEGORY_MAP = osf_settings.NODE_CATEGORY_MAP

DEBUG_TRANSACTIONS = DEBUG

JWT_SECRET = b'osf_api_cas_login_jwt_secret_32b'
JWE_SECRET = b'osf_api_cas_login_jwe_secret_32b'

ENABLE_VARNISH = osf_settings.ENABLE_VARNISH
ENABLE_ESI = osf_settings.ENABLE_ESI
VARNISH_SERVERS = osf_settings.VARNISH_SERVERS
ESI_MEDIA_TYPES = osf_settings.ESI_MEDIA_TYPES

ADDONS_FOLDER_CONFIGURABLE = ['box', 'dropbox', 's3', 'googledrive', 'figshare', 'owncloud', 'onedrive']
ADDONS_OAUTH = ADDONS_FOLDER_CONFIGURABLE + ['dataverse', 'github', 'bitbucket', 'gitlab', 'mendeley', 'zotero', 'forward']

BYPASS_THROTTLE_TOKEN = 'test-token'

OSF_SHELL_USER_IMPORTS = None

# Settings for use in the admin
OSF_URL = 'https://osf.io'

SELECT_FOR_UPDATE_ENABLED = True

# Disable anonymous user permissions in django-guardian
ANONYMOUS_USER_NAME = None

# If set to True, automated tests with extra queries will fail.
NPLUSONE_RAISE = False

# salt used for generating hashids
HASHIDS_SALT = 'pinkhimalayan'

# django-elasticsearch-metrics
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': os.environ.get('ELASTIC6_URI', '127.0.0.1:9201'),
        'retry_on_timeout': True,
    },
}
# Store yearly indices for time-series metrics
ELASTICSEARCH_METRICS_DATE_FORMAT = '%Y'

WAFFLE_CACHE_NAME = 'waffle_cache'
STORAGE_USAGE_CACHE_NAME = 'storage_usage'
STORAGE_USAGE_MAX_ENTRIES = 10000000


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    STORAGE_USAGE_CACHE_NAME: {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'osf_cache_table',
        'OPTIONS': {
            'MAX_ENTRIES': STORAGE_USAGE_MAX_ENTRIES,
        },
    },
    WAFFLE_CACHE_NAME: {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

EGAP_PROVIDER_NAME = 'EGAP'

MAX_SIZE_OF_ES_QUERY = 10000
DEFAULT_ES_NULL_VALUE = 'N/A'

TRAVIS_ENV = False
