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

LIVE_RELOAD_DOMAIN = 'http://localhost:4200'
PREPRINT_PROVIDER_DOMAINS = {
    'enabled': False,
    'prefix': 'http://local.',
    'suffix': ':4201/'
}
USE_EXTERNAL_EMBER = True
PROXY_EMBER_APPS = False
EXTERNAL_EMBER_APPS = {
    'ember_osf_web': {
        'url': '/ember_osf_web/',
        'server': 'http://localhost:4200',
        'path': '/ember_osf_web/'
    },
    'preprints': {
        'url': '/preprints/',
        'server': 'http://192.168.168.167:4201/',
        'path': '/preprints/'
    },
    'registries': {
        'url': '/registries/',
        'server': 'http://192.168.168.167:4202',
        'path': '/registries/'
    },
    'reviews': {
        'url': '/reviews/',
        'server': 'http://localhost:4203',
        'path': '/reviews/'
    }
    # 'meetings': {
    #     'url': '/meetings/',
    #     'server': 'http://localhost:4201',
    #     'path': '../osf-meetings/dist/'
    # },
}

SEARCH_ENGINE = 'elastic'
ELASTIC_TIMEOUT = 10

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

# Comment out to use celery in development
USE_CELERY = False

class CeleryConfig(defaults.CeleryConfig):
    """
    Celery configuration
    """
    ##### Celery #####
    ## Default RabbitMQ broker
    # broker_url = 'amqp://'

    # Celery with SSL
    # import ssl
    #
    # broker_use_ssl = {
    #     'keyfile': '/etc/ssl/private/worker.key',
    #     'certfile': '/etc/ssl/certs/worker.pem',
    #     'ca_certs': '/etc/ssl/certs/ca-chain.cert.pem',
    #     'cert_reqs': ssl.CERT_REQUIRED,
    # }

    # Default RabbitMQ backend
    # result_backend = 'amqp://'


USE_CDN_FOR_CLIENT_LIBS = False

# WARNING: `SENDGRID_WHITELIST_MODE` should always be True in local dev env to prevent unintentional spamming.
# Add specific email addresses to `SENDGRID_EMAIL_WHITELIST` for testing purposes.
SENDGRID_WHITELIST_MODE = True
SENDGRID_EMAIL_WHITELIST = []

# Example of extending default settings
# defaults.IMG_FMTS += ["pdf"]

# support email
OSF_SUPPORT_EMAIL = 'fake-support@osf.io'
# contact email
OSF_CONTACT_EMAIL = 'fake-contact@osf.io'
