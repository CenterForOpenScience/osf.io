# -*- coding: utf-8 -*-
"""
Base settings file, common to all environments.
These settings can be overridden in local.py.
"""

import os
import json

from api.base import settings as api_settings

os_env = os.environ


def parent_dir(path):
    '''Return the parent of a directory.'''
    return os.path.abspath(os.path.join(path, os.pardir))

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = parent_dir(HERE)  # website/ directory
APP_PATH = parent_dir(BASE_PATH)
ADDON_PATH = os.path.join(APP_PATH, 'addons')
STATIC_FOLDER = os.path.join(BASE_PATH, 'static')
STATIC_URL_PATH = '/static'
ASSET_HASH_PATH = os.path.join(APP_PATH, 'webpack-assets.json')
ROOT = os.path.join(BASE_PATH, '..')

with open(os.path.join(APP_PATH, 'package.json'), 'r') as fobj:
    VERSION = json.load(fobj)['version']

CITATION_STYLES_PATH = os.path.join(BASE_PATH, 'static', 'vendor', 'bower_components', 'styles')

LOG_PATH = os.path.join(APP_PATH, 'logs')
TEMPLATES_PATH = os.path.join(BASE_PATH, 'templates')
ANALYTICS_PATH = os.path.join(BASE_PATH, 'analytics')

# Question titles to be reomved for anonymized VOL
ANONYMIZED_TITLES = ['Authors']

LOAD_BALANCER = False
PROXY_ADDRS = []

USE_POSTGRES = True

# May set these to True in local.py for development
DEV_MODE = api_settings.DEV_MODE
DEBUG_MODE = api_settings.DEBUG_MODE
SECURE_MODE = not DEBUG_MODE  # Set secure cookie

# External Ember App Local Development
USE_EXTERNAL_EMBER = False
PROXY_EMBER_APPS = False
# http://docs.python-requests.org/en/master/user/advanced/#timeouts
EXTERNAL_EMBER_SERVER_TIMEOUT = 3.05
EXTERNAL_EMBER_APPS = {}

# local path to private key and cert for local development using https, overwrite in local.py
OSF_SERVER_KEY = None
OSF_SERVER_CERT = None

# Change if using `scripts/cron.py` to manage crontab
CRON_USER = None

# External services
USE_CDN_FOR_CLIENT_LIBS = True

# Default settings for fake email address generation
FAKE_EMAIL_NAME = 'freddiemercury'
FAKE_EMAIL_DOMAIN = 'cos.io'

# TODO: Override in local.py
MAILGUN_API_KEY = None

# File rendering timeout (in ms)
MFR_TIMEOUT = 30000

SESSION_COOKIE_SECURE = api_settings.SESSION_COOKIE_SECURE
SESSION_COOKIE_HTTPONLY = api_settings.SESSION_COOKIE_HTTPONLY

# Cache settings
SESSION_HISTORY_LENGTH = 5
SESSION_HISTORY_IGNORE_RULES = [
    lambda url: '/static/' in url,
    lambda url: 'favicon' in url,
    lambda url: url.startswith('/api/'),
]

# TODO: Configuration should not change between deploys - this should be dynamic.
CANONICAL_DOMAIN = 'openscienceframework.org'
COOKIE_DOMAIN = '.openscienceframework.org'  # Beaker
SHORT_DOMAIN = 'osf.io'

# Profile image options
PROFILE_IMAGE_LARGE = 70
PROFILE_IMAGE_MEDIUM = 40
PROFILE_IMAGE_SMALL = 20
# Currently (8/21/2017) only gravatar supported.
PROFILE_IMAGE_PROVIDER = 'gravatar'

# Conference options
CONFERENCE_MIN_COUNT = 5

NODE_CATEGORY_MAP = api_settings.NODE_CATEGORY_MAP

# Add-ons
# Load addons from addons.json
with open(os.path.join(ROOT, 'addons.json')) as fp:
    addon_settings = json.load(fp)
    ADDONS_REQUESTED = addon_settings['addons']
    ADDONS_ARCHIVABLE = addon_settings['addons_archivable']
    ADDONS_COMMENTABLE = addon_settings['addons_commentable']
    ADDONS_BASED_ON_IDS = addon_settings['addons_based_on_ids']
    ADDONS_DESCRIPTION = addon_settings['addons_description']
    ADDONS_URL = addon_settings['addons_url']
    ADDONS_DEFAULT = addon_settings['addons_default']

ADDON_CATEGORIES = [
    'documentation',
    'storage',
    'bibliography',
    'other',
    'security',
    'citations',
]

SYSTEM_ADDED_ADDONS = {
    'user': [],
    'node': [],
}

MISSING_FILE_NAME = 'untitled'

# Most Popular and New and Noteworthy Nodes
POPULAR_LINKS_NODE = None  # TODO Override in local.py in production.
POPULAR_LINKS_REGISTRATIONS = None  # TODO Override in local.py in production.
NEW_AND_NOTEWORTHY_LINKS_NODE = None  # TODO Override in local.py in production.

MAX_POPULAR_PROJECTS = 10

NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST = []  # TODO Override in local.py in production.

# FOR EMERGENCIES ONLY: Setting this to True will disable forks, registrations,
# and uploads in order to save disk space.
DISK_SAVING_MODE = False

# Seconds before another notification email can be sent to a contributor when added to a project
CONTRIBUTOR_ADDED_EMAIL_THROTTLE = 24 * 3600

# Google Analytics
GOOGLE_ANALYTICS_ID = None
GOOGLE_SITE_VERIFICATION = None

WATERBUTLER_URL = 'http://localhost:7777'
WATERBUTLER_INTERNAL_URL = WATERBUTLER_URL
WATERBUTLER_ADDRS = ['127.0.0.1']

# TODO: Remove references to this flag
ENABLE_INSTITUTIONS = True

# Used for gathering meta information about the current build
GITHUB_API_TOKEN = None

# number of nodes that need to be affiliated with an institution before the institution logo is shown on the dashboard
INSTITUTION_DISPLAY_NODE_THRESHOLD = 5
