# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/base.py

NOTE: local.py will not be added to source control.
'''

from . import base

dev_mode = True

# Change to whatever port and db you want
DB_PORT = 20771
DB_NAME = "osf20130903"
mongo_uri = 'mongodb://localhost:{port}/{db}'.format(port=DB_PORT, db=DB_NAME)

# Comment out to use solr in development
use_solr = False

# Email
mail_server = 'smtp.sendgrid.net'
mail_username = 'osf-smtp'
mail_password = 'CHANGEME'

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
# base.img_fmts += ["pdf"]
