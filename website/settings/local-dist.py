# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/base.py

NOTE: local.py will not be added to source control.
'''

from . import base

# TODO: not sure if both of these are necessary
DEV_MODE = True
DEBUG_MODE = True  # Sets the Flask app to Debug mode

# Change to whatever port and db you want
DB_PORT = 20771
DB_NAME = "osf20130903"
MONGO_URI = 'mongodb://localhost:{port}/{db}'.format(port=DB_PORT, db=DB_NAME)

# Comment out to use solr in development
USE_SOLR = False

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

# Modules to import when celery launches
CELERY_IMPORTS = (
    "framework.email.tasks",
    "framework.celery.tasks"
)

# Example of extending base settings
# base.IMG_FMTS += ["pdf"]
