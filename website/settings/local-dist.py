'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''
import logging
from os import environ

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
#GRAVYVALET_URL = 'https://localhost:8004'

PREPRINT_PROVIDER_DOMAINS = {
    'enabled': False,
    'prefix': 'http://local.',
    'suffix': ':4201/'
}
USE_EXTERNAL_EMBER = True
PROXY_EMBER_APPS = True
EMBER_DOMAIN = environ.get('EMBER_DOMAIN', 'localhost')
LIVE_RELOAD_DOMAIN = f'http://{EMBER_DOMAIN}:4200'  # Change port for the current app
EXTERNAL_EMBER_APPS = {
    'ember_osf_web': {
        'server': f'http://{EMBER_DOMAIN}:4200/',
        'path': '/ember_osf_web/',
        'routes': [
            'collections',
            'registries',
            'handbook',
        ],
    },
    'preprints': {
        'server': f'http://{EMBER_DOMAIN}:4201/',
        'path': '/preprints/'
    },
    'reviews': {
        'server': f'http://{EMBER_DOMAIN}:4203/',
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
# Cookie will be blocked if set to 'None' in local env with HTTP where COOKIE_SECURE is disabled
SESSION_COOKIE_SAMESITE = 'Lax'
OSF_SERVER_KEY = None
OSF_SERVER_CERT = None

# CEDAR API configs
CEDAR_API_HOST = ''
CEDAR_API_KEY = ''
CEDAR_HOME_FOLDER_ID = ''

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

DOI_FORMAT = '{prefix}/FK2osf.io/{guid}'

# Uncomment for local DOI creation testing
# datacite
# DATACITE_USERNAME = 'changeme'
# DATACITE_PASSWORD = 'changeme'
# DATACITE_URL = 'https://mds.test.datacite.org'

# crossref
# CROSSREF_USERNAME = 'changeme'
# CROSSREF_PASSWORD = 'changeme'
# CROSSREF_URL = https://test.crossref.org/servlet/deposit
# CROSSREF_DEPOSITOR_EMAIL = 'changeme'  # This email will receive confirmation/error messages from CrossRef on submission

CHRONOS_USE_FAKE_FILE = True
CHRONOS_FAKE_FILE_URL = 'https://staging2.osf.io/r2t5v/download'

# Show sent emails in console
logging.getLogger('website.mails.mails').setLevel(logging.DEBUG)

SHARE_ENABLED = False
DATACITE_ENABLED = False

OOPSPAM_CHECK_IP = False
USE_COLOR = False
