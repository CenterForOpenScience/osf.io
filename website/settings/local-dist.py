# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''

from . import defaults
from os import environ

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

PREPRINT_PROVIDER_DOMAINS = {
    'enabled': False,
    'prefix': 'http://local.',
    'suffix': ':4201/'
}
USE_EXTERNAL_EMBER = True
PROXY_EMBER_APPS = True
EMBER_DOMAIN = environ.get('EMBER_DOMAIN', 'localhost')
LIVE_RELOAD_DOMAIN = 'http://{}:4200'.format(EMBER_DOMAIN)  # Change port for the current app
EXTERNAL_EMBER_APPS = {
    'ember_osf_web': {
        'server': 'http://{}:4200/'.format(EMBER_DOMAIN),
        'path': '/ember_osf_web/'
    },
    'preprints': {
        'server': 'http://{}:4201/'.format(EMBER_DOMAIN),
        'path': '/preprints/'
    },
    'registries': {
        'server': 'http://{}:4202/'.format(EMBER_DOMAIN),
        'path': '/registries/'
    },
    'reviews': {
        'server': 'http://{}:4203/'.format(EMBER_DOMAIN),
        'path': '/reviews/'
    },
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

#Email templates logo
OSF_LOGO = 'osf_logo'
OSF_PREPRINTS_LOGO = 'osf_preprints'
OSF_MEETINGS_LOGO = 'osf_meetings'
OSF_PREREG_LOGO = 'osf_prereg'
OSF_REGISTRIES_LOGO = 'osf_registries'
