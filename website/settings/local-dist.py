# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''

from . import defaults

DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.
SECURE_MODE = not DEBUG_MODE  # Disable osf cookie secure

# NOTE: Internal Domains/URLs have been added to facilitate docker development environments
#       when localhost inside a container != localhost on the client machine/docker host.

PROTOCOL = 'https://' if SECURE_MODE else 'http://'
DOMAIN = PROTOCOL + 'localhost:5000/'
INTERNAL_DOMAIN = DOMAIN
API_DOMAIN = PROTOCOL + 'localhost:8000/'

#WATERBUTLER_URL = 'http://localhost:7777'
#WATERBUTLER_INTERNAL_URL = WATERBUTLER_URL

USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
    'preprints': {
        'url': '/preprints/',
        'server': 'http://localhost:4200',
        'path': '/preprints/'
    },
    # 'meetings': {
    #     'url': '/meetings/',
    #     'server': 'http://localhost:4201',
    #     'path': '../osf-meetings/dist/'
    # },
    # 'registries': {
    #     'url': '/registries/',
    #     'server': 'http://localhost:4200',
    #     'path': '../ember-osf-registries/dist/'
    # }
}

SEARCH_ENGINE = 'elastic'
ELASTIC_TIMEOUT = 10

# Comment out to use celery in development
USE_CELERY = False

# Email
USE_EMAIL = False
MAIL_SERVER = 'localhost:1025'  # For local testing
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = 'CHANGEME'

# Mailchimp email subscriptions
ENABLE_EMAIL_SUBSCRIPTIONS = False

# Session
COOKIE_NAME = 'osf'
OSF_COOKIE_DOMAIN = None
SECRET_KEY = 'CHANGEME'
SESSION_COOKIE_SECURE = SECURE_MODE
OSF_SERVER_KEY = None
OSF_SERVER_CERT = None

##### Celery #####
## Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

USE_CDN_FOR_CLIENT_LIBS = False

DISCOURSE_SSO_SECRET = 'changeme'
DISCOURSE_DEV_MODE = True
DISCOURSE_SERVER_URL = 'http://localhost:4000/' if DISCOURSE_DEV_MODE else 'http://192.168.99.100'
DISCOURSE_API_KEY = 'changeme' if DISCOURSE_DEV_MODE else 'changeme'
DISCOURSE_API_ADMIN_USER = 'system'

try:
    DISCOURSE_SERVER_SETTINGS = defaults.DISCOURSE_SERVER_SETTINGS
except AttributeError:
    DISCOURSE_SERVER_SETTINGS = {}
DISCOURSE_SERVER_SETTINGS.update({
                            'contact_email': 'changeme',
                            'logo_url': DOMAIN + 'static/img/cos-white2.png',
                            'logo_small_url': DOMAIN + 'static/img/cos-white2.png',
                            'favicon_url': DOMAIN + 'favicon.ico',
                            'sso_url': API_DOMAIN + 'v2/sso',
                            'sso_secret': DISCOURSE_SSO_SECRET,
                            'logout_redirect': DOMAIN + 'logout',
                            'cors_origins': DOMAIN,
                            'osf_domain': DOMAIN,
                            'mfr_domain': MFR_SERVER_URL,
                            })

if DISCOURSE_DEV_MODE:
    DISCOURSE_SERVER_SETTINGS.update({'port': '4000'})

# Example of extending default settings
# defaults.IMG_FMTS += ["pdf"]
