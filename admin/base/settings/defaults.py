"""
Django settings for the admin project.
"""

import os
from urlparse import urlparse
from website import settings as osf_settings
from django.contrib import messages

# import local  # Build own local.py (used with postgres)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# from the OSF settings
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = osf_settings.SECRET_KEY


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = osf_settings.DEBUG_MODE
DEBUG_PROPAGATE_EXCEPTIONS = True

ALLOWED_HOSTS = [
    '.osf.io'
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 5,
        }
    },
]

# Email settings. Account created for testing. Password shouldn't be hardcoded
# [DEVOPS] this should be set to 'django.core.mail.backends.smtp.EmailBackend' in the > dev local.py.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Sendgrid Email Settings - Using OSF credentials.
# Add settings references to local.py

EMAIL_HOST = osf_settings.MAIL_SERVER
EMAIL_HOST_USER = osf_settings.MAIL_USERNAME
EMAIL_HOST_PASSWORD = osf_settings.MAIL_PASSWORD
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'admin.common_auth',
    'admin.base',
    'admin.pre_reg',
    'admin.spam',
    'admin.metrics',
    'admin.nodes',
    'admin.users',
    'admin.desk',
    'admin.sales_analytics',

    # 3rd party
    'raven.contrib.django.raven_compat',
    'webpack_loader',
    'django_nose',
    'password_reset',
)

# Custom user model (extends AbstractBaseUser)
AUTH_USER_MODEL = 'common_auth.MyUser'

# TODO: Are there more granular ways to configure reporting specifically related to the API?
RAVEN_CONFIG = {
    'tags': {'App': 'admin'},
    'dsn': osf_settings.SENTRY_DSN,
    'release': osf_settings.VERSION,
}

# Settings related to CORS Headers addon: allow API to receive authenticated requests from OSF
# CORS plugin only matches based on "netloc" part of URL, so as workaround we add that to the list
CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = (urlparse(osf_settings.DOMAIN).netloc,
                         osf_settings.DOMAIN,
                         )
CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE_CLASSES = (
    # TokuMX transaction support
    # Needs to go before CommonMiddleware, so that transactions are always started,
    # even in the event of a redirect. CommonMiddleware may cause other middlewares'
    # process_request to be skipped, e.g. when a trailing slash is omitted
    'api.base.middleware.DjangoGlobalMiddleware',
    'api.base.middleware.MongoConnectionMiddleware',
    'api.base.middleware.CeleryTaskMiddleware',
    'api.base.middleware.TokuTransactionMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

MESSAGE_TAGS = {
    messages.SUCCESS: 'text-success',
    messages.ERROR: 'text-danger',
    messages.WARNING: 'text-warning',
}

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
        }
    }]

# Database
# Postgres:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': local.POSTGRES_NAME,
#         'USER': local.POSTGRES_USER,
#         'PASSWORD': local.POSTGRES_PASSWORD,
#         'HOST': local.POSTGRES_HOST,
#         'PORT': '',
#     }
# }
# Postgres settings in local.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

ROOT_URLCONF = 'admin.base.urls'
WSGI_APPLICATION = 'admin.base.wsgi.application'
ADMIN_BASE = ''
STATIC_URL = '/static/'
LOGIN_URL = 'account/login/'
LOGIN_REDIRECT_URL = ADMIN_BASE

STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'static_root')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)


STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

LANGUAGE_CODE = 'en-us'

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'public/js/',
        'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json'),
    }
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['--verbosity=2']

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Source'],
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList'],
            ['Link']
        ]
    },
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allaccess.backends.AuthorizedServiceBackend',
)

# Keen.io settings in local.py
KEEN_PROJECT_ID = osf_settings.KEEN_PROJECT_ID
KEEN_READ_KEY = osf_settings.KEEN_READ_KEY
KEEN_WRITE_KEY = osf_settings.KEEN_WRITE_KEY

KEEN_CREDENTIALS = {
    'keen_ready': False
}

if KEEN_CREDENTIALS['keen_ready']:
    KEEN_CREDENTIALS.update({
        'keen_project_id': KEEN_PROJECT_ID,
        'keen_read_key': KEEN_READ_KEY,
        'keen_write_key': KEEN_WRITE_KEY
    })


ENTRY_POINTS = {'osf4m': 'osf4m', 'prereg_challenge_campaign': 'prereg',
                'institution_campaign': 'institution'}
