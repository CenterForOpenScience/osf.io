# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''

from . import defaults

DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.

# Comment out to use solr in development
USE_SOLR = True

# Comment out to use celery in development
USE_CELERY = True

# Which addons are enabled
ADDONS_REQUESTED = [
    'wiki', 'osffiles',
    'github', 's3', 'figshare',
    'dropbox',
    # 'badges', 'forward',
]

# Email
MAIL_SERVER = 'localhost:1025'  # For local testing
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = 'CHANGEME'

# Session
COOKIE_NAME = 'osf'
SECRET_KEY = "CHANGEME"

##### Celery #####
## Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

USE_CDN_FOR_CLIENT_LIBS = False

# Example of extending default settings
# defaults.IMG_FMTS += ["pdf"]

# Staging credentials (may be used for development)

# PIWIK_HOST = 'http://162.243.104.66/piwik/'
# PIWIK_ADMIN_TOKEN = '6e9b2daf6c9dacd2eddbba5083b058fa'
# PIWIK_SITE_ID = 1
