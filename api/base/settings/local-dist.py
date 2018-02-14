from .defaults import *  # noqa


DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.
SECURE_MODE = not DEBUG_MODE  # Disable osf secure cookie

VARNISH_SERVERS = ['http://127.0.0.1:8080']
ENABLE_VARNISH = False
ENABLE_ESI = False
CORS_ORIGIN_ALLOW_ALL = True

# Uncomment to get real tracebacks while testing
# DEBUG_PROPAGATE_EXCEPTIONS = True

if DEBUG_MODE:
    INSTALLED_APPS += ('debug_toolbar', 'nplusone.ext.django',)
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', 'nplusone.ext.django.NPlusOneMiddleware',)
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda(_): True
    }
    ALLOWED_HOSTS.append('localhost')


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'user': '1000000/second',
    'non-cookie-auth': '1000000/second',
    'add-contributor': '1000000/second',
    'create-guid': '1000000/second',
    'root-anon-throttle': '1000000/second',
    'test-user': '2/hour',
    'test-anon': '1/hour',
}

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

class CeleryConfig(CeleryConfig):
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

# NOTE: Internal Domains/URLs have been added to facilitate docker development environments
#       when localhost inside a container != localhost on the client machine/docker host.

PROTOCOL = 'https://' if SECURE_MODE else 'http://'
DOMAIN = PROTOCOL + 'localhost:5000/'
INTERNAL_DOMAIN = DOMAIN
API_DOMAIN = PROTOCOL + 'localhost:8000/'

LIVE_RELOAD_DOMAIN = 'http://localhost:4200'
PREPRINT_PROVIDER_DOMAINS = {
    'enabled': False,
    'prefix': 'http://local.',
    'suffix': ':4201/'
}

SEARCH_ENGINE = 'elastic'
ELASTIC_TIMEOUT = 10

# WARNING: `SENDGRID_WHITELIST_MODE` should always be True in local dev env to prevent unintentional spamming.
# Add specific email addresses to `SENDGRID_EMAIL_WHITELIST` for testing purposes.
SENDGRID_WHITELIST_MODE = True
SENDGRID_EMAIL_WHITELIST = []

# support email
OSF_SUPPORT_EMAIL = 'fake-support@osf.io'
