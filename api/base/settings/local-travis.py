from .defaults import *  # noqa


VARNISH_SERVERS = ['http://127.0.0.1:8080']
ENABLE_VARNISH = True
ENABLE_ESI = False


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'user': '1000000/second',
    'non-cookie-auth': '1000000/second',
    'add-contributor': '1000000/second',
    'create-guid': '1000000/second',
    'root-anon-throttle': '1000000/second',
    'test-user': '2/hour',
    'test-anon': '1/hour',
}

ALLOWED_HOSTS.append('localhost')

DB_PORT = 54321

DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.
SECURE_MODE = not DEBUG_MODE  # Disable osf secure cookie
DEBUG = DEBUG_MODE

PROTOCOL = 'https://' if SECURE_MODE else 'http://'
DOMAIN = PROTOCOL + 'localhost:5000/'
API_DOMAIN = PROTOCOL + 'localhost:8000/'

PREPRINT_PROVIDER_DOMAINS = {
    'enabled': False,
    'prefix': 'http://local.',
    'suffix': ':4201/'
}

SEARCH_ENGINE = 'elastic'

USE_EMAIL = False
USE_CELERY = False

# Email
MAIL_SERVER = 'localhost:1025'  # For local testing
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = 'CHANGEME'

# Session
COOKIE_NAME = 'osf'
SECRET_KEY = 'CHANGEME'
SESSION_COOKIE_SECURE = SECURE_MODE
OSF_SERVER_KEY = None
OSF_SERVER_CERT = None

class CeleryConfig(CeleryConfig):
    """
    Celery configuration
    """
    ## Default RabbitMQ broker
    broker_url = 'amqp://'

    # In-memory result backend
    result_backend = 'cache'
    cache_backend = 'memory'

SENTRY_DSN = None

# if ENABLE_VARNISH isn't set in python read it from the env var and set it
locals().setdefault('ENABLE_VARNISH', os.environ.get('ENABLE_VARNISH') == 'True')

KEEN = {
    'public': {
        'project_id': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
        'master_key': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
        'write_key': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
        'read_key': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
    },
    'private': {
        'project_id': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
        'write_key': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
        'read_key': '123456789abcdef101112131415161718191a1b1c1d1e1f20212223242526272',
    },
}

NEW_AND_NOTEWORTHY_LINKS_NODE = 'helloo'
POPULAR_LINKS_NODE = 'hiyah'
POPULAR_LINKS_REGISTRATIONS = 'woooo'

EZID_USERNAME = 'testfortravisnotreal'
EZID_PASSWORD = 'testfortravisnotreal'

logging.getLogger('celery.app.trace').setLevel(logging.FATAL)
