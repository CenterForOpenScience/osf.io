# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''
import inspect

from . import defaults
import os

DB_PORT = 27017

DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.
SECURE_MODE = not DEBUG_MODE  # Disable secure and httponly cookie

PROTOCOL = 'https://' if SECURE_MODE else 'http://'
DOMAIN = PROTOCOL + 'localhost:5000/'
API_DOMAIN = PROTOCOL + 'localhost:8000/'

SEARCH_ENGINE = 'elastic'

USE_EMAIL = False
USE_CELERY = False
USE_GNUPG = False

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

##### Celery #####
## Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

USE_CDN_FOR_CLIENT_LIBS = False

SENTRY_DSN = None

TEST_DB_NAME = DB_NAME = 'osf_test'

VARNISH_SERVERS = ['http://localhost:8080']

# if ENABLE_VARNISH isn't set in python read it from the env var and set it
locals().setdefault('ENABLE_VARNISH', os.environ.get('ENABLE_VARNISH') == 'True')
