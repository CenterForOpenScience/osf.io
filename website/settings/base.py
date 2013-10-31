# -*- coding: utf-8 -*-
'''Base settings file, common to all environments.

These settings can be overridden in local.py.
'''
import os

def parent_dir(path):
    '''Return the parent of a directory.'''
    return os.path.abspath(os.path.join(path, os.pardir))

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = parent_dir(HERE)  # website/ directory
STATIC_FOLDER = os.path.join(BASE_PATH, 'static')
STATIC_URL_PATH = "/static"
TEMPLATES_PATH = os.path.join(BASE_PATH, "templates")


# User management & registration
CONFIRM_REGISTRATIONS_BY_EMAIL = False # Not fully implemented
ALLOW_REGISTRATION = True
ALLOW_LOGIN = True

USE_SOLR = True
solr = 'http://localhost:8983/solr/'

# Sessions
COOKIE_NAME = 'osf'
SECRET_KEY = "CHANGEME"

try:
    os.environ['OSF_PRODUCTION']
    DEBUG_MODE = False
except KeyError:
    DEBUG_MODE = True

# External services
try:
    os.environ['OSF_PRODUCTION']
    USE_CDN_FOR_CLIENT_LIBS = True
except KeyError:
    USE_CDN_FOR_CLIENT_LIBS = False


FROM_EMAIL = "openscienceframework-noreply@openscienceframework.org"
MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = ''  # Set this in local.py

try:
    os.environ['OSF_PRODUCTION']
    CACHE_PATH = '/opt/data/osf_cache'
    UPLOADS_PATH = '/opt/data/uploads'
except KeyError:
    CACHE_PATH = os.path.join(BASE_PATH, 'cache')
    UPLOADS_PATH = os.path.join(BASE_PATH, 'uploads')

DB_PORT = 20771
DB_NAME = "osf20130903"
if os.environ.get("OSF_PRODUCTION", False):
    MONGO_URI = 'mongodb://osf:osfosfosfosf0$f@localhost:{0}/{1}'.format(DB_PORT, DB_NAME)
else:
    MONGO_URI = 'mongodb://localhost:{0}/{1}'.format(DB_PORT, DB_NAME)

#TODO: Configuration should not change between deploys - this should be dynamic.
CANONICAL_DOMAIN = 'openscienceframework.org'
COOKIE_DOMAIN = '.openscienceframework.org' # Beaker

# Gravatar options
GRAVATAR_SIZE_PROFILE = 120
GRAVATAR_SIZE_ADD_CONTRIBUTOR = 80

# File upload options
MAX_UPLOAD_SIZE = 1024*1024*250     # In bytes

# File render options
MAX_RENDER_SIZE = 1024*1024*2.5     # In bytes
IMG_FMTS = ['jpe?g', 'tiff?', 'png', 'gif', 'bmp', 'svg', 'ico']
RENDER_ZIP = True
RENDER_TAR = True
ARCHIVE_DEPTH = 2               # Set to None for unlimited depth

# User activity style
USER_ACTIVITY_MAX_WIDTH = 325

WIKI_WHITELIST = {
    'tags': [
        'a', 'abbr', 'acronym', 'b', 'bdo', 'big', 'blockquote', 'br',
        'center', 'cite', 'code',
        'dd', 'del', 'dfn', 'div', 'dl', 'dt', 'em', 'embed', 'font',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'ins',
        'kbd', 'li', 'object', 'ol', 'param', 'pre', 'p', 'q',
        's', 'samp', 'small', 'span', 'strike', 'strong', 'sub', 'sup',
        'table', 'tbody', 'td', 'th', 'thead', 'tr', 'tt', 'ul', 'u',
        'var', 'wbr',
    ],
    'attributes': [
        'align', 'alt', 'border', 'cite', 'class', 'dir',
        'height', 'href', 'src', 'style', 'title', 'type', 'width',
        'face', 'size', # font tags
        'salign', 'align', 'wmode', 'target',
    ],
    # Styles currently used in Reproducibility Project wiki pages
    # TODO: Discuss and possibly delete
    'styles' : [
        'top', 'left', 'width', 'height', 'position',
        'background', 'font-size', 'text-align', 'z-index',
        'list-style',
    ]
}

try:
    os.environ['OSF_PRODUCTION']
    DEV_MODE = False
except KeyError:
    DEV_MODE = True


##### Celery #####
## Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

# Modules to import when celery launches
CELERY_IMPORTS = (
    "framework.email.tasks",
    "framework.tasks"
)
