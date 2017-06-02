"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 1.8.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os
from urlparse import urlparse
from website import settings as osf_settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

DATABASES = {
    'default': {
        'CONN_MAX_AGE': 0,
        'ENGINE': 'osf.db.backends.postgresql',  # django.db.backends.postgresql
        'NAME': os.environ.get('OSF_DB_NAME', 'osf'),
        'USER': os.environ.get('OSF_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('OSF_DB_PASSWORD', ''),
        'HOST': os.environ.get('OSF_DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('OSF_DB_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
    }
}

DATABASE_ROUTERS = ['osf.db.router.PostgreSQLFailoverRouter', ]
CELERY_IMPORTS = [
    'osf.management.commands.migratedata',
    'osf.management.commands.migraterelations',
    'osf.management.commands.verify',
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

AUTH_USER_MODEL = 'osf.OSFUser'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = osf_settings.SECRET_KEY

AUTHENTICATION_BACKENDS = (
    'api.base.authentication.backends.ODMBackend',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEV_MODE = osf_settings.DEV_MODE
DEBUG = osf_settings.DEBUG_MODE
DEBUG_PROPAGATE_EXCEPTIONS = True

# session:
SESSION_COOKIE_NAME = 'api'
SESSION_COOKIE_SECURE = osf_settings.SECURE_MODE
SESSION_COOKIE_HTTPONLY = osf_settings.SESSION_COOKIE_HTTPONLY

# csrf:
CSRF_COOKIE_NAME = 'api-csrf'
CSRF_COOKIE_SECURE = osf_settings.SECURE_MODE
CSRF_COOKIE_HTTPONLY = osf_settings.SECURE_MODE

ALLOWED_HOSTS = [
    '.osf.io'
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
    'rest_framework',
    'rest_framework_swagger',
    'corsheaders',
    'raven.contrib.django.raven_compat',
    'django_extensions',

    # OSF
    'osf',

    # Addons
    'addons.osfstorage',
    'addons.box',
    'addons.dataverse',
    'addons.dropbox',
    'addons.figshare',
    'addons.forward',
    'addons.github',
    'addons.googledrive',
    'addons.mendeley',
    'addons.owncloud',
    'addons.s3',
    'addons.twofactor',
    'addons.wiki',
    'addons.zotero',
    'addons.swift',
    'addons.azureblobstorage'
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
    'DEFAULT_BULK_LIMIT': 100
}

MAX_PAGE_SIZE = 100

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    # Order is important here because of a bug in rest_framework_swagger. For now,
    # rest_framework.renderers.JSONRenderer needs to be first, at least until
    # https://github.com/marcgibbons/django-rest-swagger/issues/271 is resolved.
    'DEFAULT_RENDERER_CLASSES': (
        'api.base.renderers.JSONAPIRenderer',
        'api.base.renderers.JSONRendererWithESISupport',
        'api.base.renderers.BrowsableAPIRendererNoForms',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'api.base.parsers.JSONAPIParser',
        'api.base.parsers.JSONAPIParserForRegularJSON',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
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
    ),
    'DEFAULT_FILTER_BACKENDS': ('api.base.filters.ODMOrderingFilter',),
    'DEFAULT_PAGINATION_CLASS': 'api.base.pagination.JSONAPIPagination',
    'ORDERING_PARAM': 'sort',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Custom auth classes
        'api.base.authentication.drf.OSFBasicAuthentication',
        'api.base.authentication.drf.OSFSessionAuthentication',
        'api.base.authentication.drf.OSFCASAuthentication'
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
        'api.base.throttling.NonCookieAuthThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/day',
        'non-cookie-auth': '100/hour',
        'add-contributor': '10/second',
        'create-guid': '1000/hour',
        'root-anon-throttle': '1000/hour',
        'test-user': '2/hour',
        'test-anon': '1/hour',
    }
}

# Settings related to CORS Headers addon: allow API to receive authenticated requests from OSF
# CORS plugin only matches based on "netloc" part of URL, so as workaround we add that to the list
CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = (urlparse(osf_settings.DOMAIN).netloc,
                         osf_settings.DOMAIN,
                         )
# This needs to remain True to allow cross origin requests that are in CORS_ORIGIN_WHITELIST to
# use cookies.
CORS_ALLOW_CREDENTIALS = True
# Set dynamically on app init
ORIGINS_WHITELIST = ()

MIDDLEWARE_CLASSES = (
    'api.base.middleware.DjangoGlobalMiddleware',
    'api.base.middleware.CeleryTaskMiddleware',
    'api.base.middleware.PostcommitTaskMiddleware',

    # A profiling middleware. ONLY FOR DEV USE
    # Uncomment and add "prof" to url params to recieve a profile for that url
    # 'api.base.middleware.ProfileMiddleware',

    # 'django.contrib.sessions.middleware.SessionMiddleware',
    'api.base.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True
    }]


ROOT_URLCONF = 'api.base.urls'
WSGI_APPLICATION = 'api.base.wsgi.application'


LANGUAGE_CODE = 'en-us'

# Disabled to make a test work (TestNodeLog.test_formatted_date)
# TODO Try to understand what's happening to cause the test to break when that line is active.
# TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static/vendor')

API_BASE = 'v2/'
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    ('rest_framework_swagger/css', os.path.join(BASE_DIR, 'static/css')),
    ('rest_framework_swagger/images', os.path.join(BASE_DIR, 'static/images')),
)

# TODO: Revisit methods for excluding private routes from swagger docs
SWAGGER_SETTINGS = {
    'api_path': '/',
    'info': {
        'description':
        """
        Welcome to the fine documentation for the Open Science Framework's API!  Please click
        on the <strong>GET /v2/</strong> link below to get started.

        For the most recent docs, please check out our <a href="/v2/">Browsable API</a>.
        """,
        'title': 'OSF APIv2 Documentation',
    },
    'doc_expansion': 'list',
    'exclude_namespaces': ['applications', 'tokens', 'test'],
}

NODE_CATEGORY_MAP = osf_settings.NODE_CATEGORY_MAP

DEBUG_TRANSACTIONS = DEBUG

JWT_SECRET = 'osf_api_cas_login_jwt_secret_32b'
JWE_SECRET = 'osf_api_cas_login_jwe_secret_32b'

ENABLE_VARNISH = osf_settings.ENABLE_VARNISH
ENABLE_ESI = osf_settings.ENABLE_ESI
VARNISH_SERVERS = osf_settings.VARNISH_SERVERS
ESI_MEDIA_TYPES = osf_settings.ESI_MEDIA_TYPES

ADDONS_FOLDER_CONFIGURABLE = ['box', 'dropbox', 's3', 'googledrive', 'figshare', 'owncloud', 'swift', 'azureblobstorage']
ADDONS_OAUTH = ADDONS_FOLDER_CONFIGURABLE + ['dataverse', 'github', 'mendeley', 'zotero', 'forward']

BYPASS_THROTTLE_TOKEN = 'test-token'

OSF_SHELL_USER_IMPORTS = None

# Settings for use in the admin
OSF_URL = 'https://osf.io'
