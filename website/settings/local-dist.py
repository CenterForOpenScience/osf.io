# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''

from . import defaults

DEV_MODE = True
DEBUG_MODE = True  # Sets app to debug mode, turns off template caching, etc.

# Comment out to use solr in development
SEARCH_ENGINE = 'elastic'
ELASTIC_TIMEOUT = 10

# Comment out to use celery in development
USE_CELERY = False

# Comment out to use GnuPG in development
USE_GNUPG = False  # Changing this may require you to re-enter encrypted fields

# Email
USE_EMAIL = False
MAIL_SERVER = 'localhost:1025'  # For local testing
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = 'CHANGEME'

# Session
COOKIE_NAME = 'osf'
SECRET_KEY = "CHANGEME"

# Uncomment if GPG was installed with homebrew
# GNUPG_BINARY = '/usr/local/bin/gpg'

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

SENTRY_DSN = "<INSERT DSN HERE>"
