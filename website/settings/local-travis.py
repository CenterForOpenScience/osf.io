# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''
import inspect
import logging

from . import defaults
import os

DB_PORT = 54321

DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.
SECURE_MODE = not DEBUG_MODE  # Disable osf secure cookie

PROTOCOL = 'https://' if SECURE_MODE else 'http://'
DOMAIN = PROTOCOL + 'localhost:5000/'
API_DOMAIN = PROTOCOL + 'localhost:8000/'
ENABLE_INSTITUTIONS = True

PREPRINT_PROVIDER_DOMAINS = {
    'enabled': False,
    'prefix': 'http://local.',
    'suffix': ':4201/'
}
USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
    'ember_osf_web': {
        'server': 'http://localhost:4200',
        'path': os.environ.get('HOME') + '/ember_osf_web/'
    },
    'preprints': {
        'server': 'http://localhost:4201',
        'path': os.environ.get('HOME') + '/preprints/'
    }
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
SECRET_KEY = "CHANGEME"
SESSION_COOKIE_SECURE = SECURE_MODE
OSF_SERVER_KEY = None
OSF_SERVER_CERT = None

class CeleryConfig(defaults.CeleryConfig):
    """
    Celery configuration
    """
    ## Default RabbitMQ broker
    broker_url = 'amqp://'

    # In-memory result backend
    result_backend = 'cache'
    cache_backend = 'memory'

USE_CDN_FOR_CLIENT_LIBS = False

SENTRY_DSN = None

TEST_DB_NAME = DB_NAME = 'osf_test'

VARNISH_SERVERS = ['http://localhost:8080']

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

logging.getLogger('celery.app.trace').setLevel(logging.FATAL)
