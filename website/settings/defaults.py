# -*- coding: utf-8 -*-
"""
Base settings file, common to all environments.
These settings can be overridden in local.py.
"""

import os
import json
import hashlib



os_env = os.environ

def parent_dir(path):
    '''Return the parent of a directory.'''
    return os.path.abspath(os.path.join(path, os.pardir))

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = parent_dir(HERE)  # website/ directory
APP_PATH = parent_dir(BASE_PATH)
ADDON_PATH = os.path.join(BASE_PATH, 'addons')
STATIC_FOLDER = os.path.join(BASE_PATH, 'static')
STATIC_URL_PATH = '/static'
ASSET_HASH_PATH = os.path.join(APP_PATH, 'webpack-assets.json')
ROOT = os.path.join(BASE_PATH, '..')

# Hours before email confirmation tokens expire
EMAIL_TOKEN_EXPIRATION = 24
CITATION_STYLES_PATH = os.path.join(BASE_PATH, 'static', 'vendor', 'bower_components', 'styles')

LOAD_BALANCER = False
PROXY_ADDRS = []

LOG_PATH = os.path.join(APP_PATH, 'logs')
TEMPLATES_PATH = os.path.join(BASE_PATH, 'templates')
ANALYTICS_PATH = os.path.join(BASE_PATH, 'analytics')

CORE_TEMPLATES = os.path.join(BASE_PATH, 'templates/log_templates.mako')
BUILT_TEMPLATES = os.path.join(BASE_PATH, 'templates/_log_templates.mako')

DOMAIN = 'http://localhost:5000/'
GNUPG_HOME = os.path.join(BASE_PATH, 'gpg')
GNUPG_BINARY = 'gpg'

# User management & registration
CONFIRM_REGISTRATIONS_BY_EMAIL = True
ALLOW_REGISTRATION = True
ALLOW_LOGIN = True

SEARCH_ENGINE = 'elastic'  # Can be 'elastic', or None
ELASTIC_URI = 'localhost:9200'
ELASTIC_TIMEOUT = 10
SHARE_ELASTIC_URI = ELASTIC_URI
# Sessions
# TODO: Override SECRET_KEY in local.py in production
COOKIE_NAME = 'osf'
SECRET_KEY = 'CHANGEME'

# May set these to True in local.py for development
DEV_MODE = False
DEBUG_MODE = False


# TODO: Remove after migration to OSF Storage
COPY_GIT_REPOS = False

# External services
USE_CDN_FOR_CLIENT_LIBS = True

USE_EMAIL = True
FROM_EMAIL = 'openscienceframework-noreply@osf.io'
MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = ''  # Set this in local.py

# Mandrill
MANDRILL_USERNAME = None
MANDRILL_PASSWORD = None
MANDRILL_MAIL_SERVER = None

# Mailchimp
MAILCHIMP_API_KEY = None
MAILCHIMP_WEBHOOK_SECRET_KEY = 'CHANGEME'  # OSF secret key to ensure webhook is secure
ENABLE_EMAIL_SUBSCRIPTIONS = True
MAILCHIMP_GENERAL_LIST = 'Open Science Framework General'

# TODO: Override in local.py
MAILGUN_API_KEY = None

# TODO: Override in local.py in production
UPLOADS_PATH = os.path.join(BASE_PATH, 'uploads')
MFR_CACHE_PATH = os.path.join(BASE_PATH, 'mfrcache')
MFR_TEMP_PATH = os.path.join(BASE_PATH, 'mfrtemp')

# Use Celery for file rendering
USE_CELERY = True

# Use GnuPG for encryption
USE_GNUPG = True

# File rendering timeout (in ms)
MFR_TIMEOUT = 30000

# TODO: Override in local.py in production
USE_TOKU_MX = True
DB_HOST = 'localhost'
DB_PORT = os_env.get('OSF_DB_PORT', 27017)
DB_NAME = 'osf20130903'
DB_USER = None
DB_PASS = None

# Cache settings
SESSION_HISTORY_LENGTH = 5
SESSION_HISTORY_IGNORE_RULES = [
    lambda url: '/static/' in url,
    lambda url: 'favicon' in url,
]

# TODO: Configuration should not change between deploys - this should be dynamic.
CANONICAL_DOMAIN = 'openscienceframework.org'
COOKIE_DOMAIN = '.openscienceframework.org' # Beaker
SHORT_DOMAIN = 'osf.io'

# TODO: Combine Python and JavaScript config
COMMENT_MAXLENGTH = 500

# Gravatar options
GRAVATAR_SIZE_PROFILE = 70
GRAVATAR_SIZE_ADD_CONTRIBUTOR = 40
GRAVATAR_SIZE_DISCUSSION = 20

# Conference options
CONFERNCE_MIN_COUNT = 5

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
        'height', 'href', 'id', 'src', 'style', 'title', 'type', 'width',
        'face', 'size', # font tags
        'salign', 'align', 'wmode', 'target',
    ],
    # Styles currently used in Reproducibility Project wiki pages
    'styles' : [
        'top', 'left', 'width', 'height', 'position',
        'background', 'font-size', 'text-align', 'z-index',
        'list-style',
    ]
}

##### Celery #####
## Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

# Modules to import when celery launches
CELERY_IMPORTS = (
    'framework.tasks',
    'framework.tasks.signals',
    'framework.email.tasks',
    'framework.render.tasks',
    'framework.analytics.tasks',
    'website.mailchimp_utils',
    'website.notifications.emails',
    'website.util.send_digest'
)

# Add-ons

# Load addons from addons.json
with open(os.path.join(ROOT, 'addons.json')) as fp:
    ADDONS_REQUESTED = json.load(fp)['addons']

ADDON_CATEGORIES = [
    'documentation',
    'storage',
    'bibliography',
    'other',
    'security',
]

SYSTEM_ADDED_ADDONS = {
    # 'user': ['badges'],
    'user': [],
    'node': [],
}

# Piwik

# TODO: Override in local.py in production
PIWIK_HOST = None
PIWIK_ADMIN_TOKEN = None
PIWIK_SITE_ID = None

SENTRY_DSN = None
SENTRY_DSN_JS = None


# TODO: Delete me after merging GitLab
MISSING_FILE_NAME = 'untitled'

# Dashboard
ALL_MY_PROJECTS_ID = '-amp'
ALL_MY_REGISTRATIONS_ID = '-amr'
ALL_MY_PROJECTS_NAME = 'All my projects'
ALL_MY_REGISTRATIONS_NAME = 'All my registrations'

# FOR EMERGENCIES ONLY: Setting this to True will disable forks, registrations,
# and uploads in order to save disk space.
DISK_SAVING_MODE = False

# Add Contributors (most in common)
MAX_MOST_IN_COMMON_LENGTH = 15

# Google Analytics
GOOGLE_ANALYTICS_ID = None
GOOGLE_SITE_VERIFICATION = None

# Pingdom
PINGDOM_ID = None

DEFAULT_HMAC_SECRET = 'changeme'
DEFAULT_HMAC_ALGORITHM = hashlib.sha256
WATERBUTLER_URL = 'http://localhost:7777'
WATERBUTLER_ADDRS = ['127.0.0.1']
