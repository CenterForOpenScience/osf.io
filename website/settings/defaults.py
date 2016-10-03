# -*- coding: utf-8 -*-
"""
Base settings file, common to all environments.
These settings can be overridden in local.py.
"""

import datetime
import os
import json
import hashlib
from datetime import timedelta
from collections import OrderedDict

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
BCRYPT_LOG_ROUNDS = 12

with open(os.path.join(APP_PATH, 'package.json'), 'r') as fobj:
    VERSION = json.load(fobj)['version']

# Expiration time for verification key
EXPIRATION_TIME_DICT = {
    'password': 30,         # 30 minutes for forgot and reset password
    'confirm': 24 * 60,     # 24 hours in minutes for confirm account and email
    'claim': 30 * 24 * 60   # 30 days in minutes for claim contributor-ship
}

CITATION_STYLES_PATH = os.path.join(BASE_PATH, 'static', 'vendor', 'bower_components', 'styles')

# Minimum seconds between forgot password email attempts
SEND_EMAIL_THROTTLE = 30

# Hours before pending embargo/retraction/registration automatically becomes active
RETRACTION_PENDING_TIME = datetime.timedelta(days=2)
EMBARGO_PENDING_TIME = datetime.timedelta(days=2)
EMBARGO_TERMINATION_PENDING_TIME = datetime.timedelta(days=2)
REGISTRATION_APPROVAL_TIME = datetime.timedelta(days=2)
# Date range for embargo periods
EMBARGO_END_DATE_MIN = datetime.timedelta(days=2)
EMBARGO_END_DATE_MAX = datetime.timedelta(days=1460)  # Four years
# Question titles to be reomved for anonymized VOL
ANONYMIZED_TITLES = ['Authors']

LOAD_BALANCER = False
PROXY_ADDRS = []

# May set these to True in local.py for development
DEV_MODE = False
DEBUG_MODE = False
SECURE_MODE = not DEBUG_MODE  # Set secure cookie

PROTOCOL = 'https://' if SECURE_MODE else 'http://'
DOMAIN = PROTOCOL + 'localhost:5000/'
API_DOMAIN = PROTOCOL + 'localhost:8000/'

# External Ember App Local Development
USE_EXTERNAL_EMBER = False
EXTERNAL_EMBER_APPS = {}

LOG_PATH = os.path.join(APP_PATH, 'logs')
TEMPLATES_PATH = os.path.join(BASE_PATH, 'templates')
ANALYTICS_PATH = os.path.join(BASE_PATH, 'analytics')

GNUPG_HOME = os.path.join(BASE_PATH, 'gpg')
GNUPG_BINARY = 'gpg'

# User management & registration
CONFIRM_REGISTRATIONS_BY_EMAIL = True
ALLOW_REGISTRATION = True
ALLOW_LOGIN = True

SEARCH_ENGINE = 'elastic'  # Can be 'elastic', or None
ELASTIC_URI = 'localhost:9200'
ELASTIC_TIMEOUT = 10
ELASTIC_INDEX = 'website'

# Sessions
COOKIE_NAME = 'osf'
# TODO: Override OSF_COOKIE_DOMAIN in local.py in production
OSF_COOKIE_DOMAIN = None
# server-side verification timeout
OSF_SESSION_TIMEOUT = 30 * 24 * 60 * 60  # 30 days in seconds
# TODO: Override SECRET_KEY in local.py in production
SECRET_KEY = 'CHANGEME'
SESSION_COOKIE_SECURE = SECURE_MODE
SESSION_COOKIE_HTTPONLY = True

# local path to private key and cert for local development using https, overwrite in local.py
OSF_SERVER_KEY = None
OSF_SERVER_CERT = None

# Change if using `scripts/cron.py` to manage crontab
CRON_USER = None

# External services
USE_CDN_FOR_CLIENT_LIBS = True

USE_EMAIL = True
FROM_EMAIL = 'openscienceframework-noreply@osf.io'
SUPPORT_EMAIL = 'support@osf.io'

# SMTP Settings
MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = ''  # Set this in local.py

# OR, if using Sendgrid's API
SENDGRID_API_KEY = None

# Mailchimp
MAILCHIMP_API_KEY = None
MAILCHIMP_WEBHOOK_SECRET_KEY = 'CHANGEME'  # OSF secret key to ensure webhook is secure
ENABLE_EMAIL_SUBSCRIPTIONS = True
MAILCHIMP_GENERAL_LIST = 'Open Science Framework General'

#Triggered emails
OSF_HELP_LIST = 'Open Science Framework Help'
WAIT_BETWEEN_MAILS = timedelta(days=7)
NO_ADDON_WAIT_TIME = timedelta(weeks=8)
NO_LOGIN_WAIT_TIME = timedelta(weeks=4)
WELCOME_OSF4M_WAIT_TIME = timedelta(weeks=2)
NO_LOGIN_OSF4M_WAIT_TIME = timedelta(weeks=6)
NEW_PUBLIC_PROJECT_WAIT_TIME = timedelta(hours=24)
WELCOME_OSF4M_WAIT_TIME_GRACE = timedelta(days=12)

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
    lambda url: url.startswith('/api/'),
]

# TODO: Configuration should not change between deploys - this should be dynamic.
CANONICAL_DOMAIN = 'openscienceframework.org'
COOKIE_DOMAIN = '.openscienceframework.org'  # Beaker
SHORT_DOMAIN = 'osf.io'

# TODO: Combine Python and JavaScript config
COMMENT_MAXLENGTH = 500

# Profile image options
PROFILE_IMAGE_LARGE = 70
PROFILE_IMAGE_MEDIUM = 40
PROFILE_IMAGE_SMALL = 20

# Conference options
CONFERENCE_MIN_COUNT = 5

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

# Maps category identifier => Human-readable representation for use in
# titles, menus, etc.
# Use an OrderedDict so that menu items show in the correct order
NODE_CATEGORY_MAP = OrderedDict([
    ('analysis', 'Analysis'),
    ('communication', 'Communication'),
    ('data', 'Data'),
    ('hypothesis', 'Hypothesis'),
    ('instrumentation', 'Instrumentation'),
    ('methods and measures', 'Methods and Measures'),
    ('procedure', 'Procedure'),
    ('project', 'Project'),
    ('software', 'Software'),
    ('other', 'Other'),
    ('', 'Uncategorized')
])

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

ADDON_CATEGORIES = [
    'documentation',
    'storage',
    'bibliography',
    'other',
    'security',
    'citations',
]

SYSTEM_ADDED_ADDONS = {
    # 'user': ['badges'],
    'user': [],
    'node': [],
}

KEEN = {
    'public': {
        'project_id': None,
        'master_key': 'changeme',
        'write_key': '',
        'read_key': '',
    },
    'private': {
        'project_id': '',
        'write_key': '',
        'read_key': '',
    },
}

SENTRY_DSN = None
SENTRY_DSN_JS = None


# TODO: Delete me after merging GitLab
MISSING_FILE_NAME = 'untitled'

# Project Organizer
ALL_MY_PROJECTS_ID = '-amp'
ALL_MY_REGISTRATIONS_ID = '-amr'
ALL_MY_PROJECTS_NAME = 'All my projects'
ALL_MY_REGISTRATIONS_NAME = 'All my registrations'

# Most Popular and New and Noteworthy Nodes
POPULAR_LINKS_NODE = None  # TODO Override in local.py in production.
NEW_AND_NOTEWORTHY_LINKS_NODE = None  # TODO Override in local.py in production.

NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST = []  # TODO Override in local.py in production.

# FOR EMERGENCIES ONLY: Setting this to True will disable forks, registrations,
# and uploads in order to save disk space.
DISK_SAVING_MODE = False

# Seconds before another notification email can be sent to a contributor when added to a project
CONTRIBUTOR_ADDED_EMAIL_THROTTLE = 24 * 3600

# Google Analytics
GOOGLE_ANALYTICS_ID = None
GOOGLE_SITE_VERIFICATION = None

# Pingdom
PINGDOM_ID = None

DEFAULT_HMAC_SECRET = 'changeme'
DEFAULT_HMAC_ALGORITHM = hashlib.sha256
WATERBUTLER_URL = 'http://localhost:7777'
WATERBUTLER_ADDRS = ['127.0.0.1']

# Test identifier namespaces
DOI_NAMESPACE = 'doi:10.5072/FK2'
ARK_NAMESPACE = 'ark:99999/fk4'

EZID_USERNAME = 'changeme'
EZID_PASSWORD = 'changeme'
# Format for DOIs and ARKs
EZID_FORMAT = '{namespace}osf.io/{guid}'

SHARE_REGISTRATION_URL = ''
SHARE_URL = 'https://share.osf.io/'

CAS_SERVER_URL = 'http://localhost:8080'
MFR_SERVER_URL = 'http://localhost:7778'

###### ARCHIVER ###########
ARCHIVE_PROVIDER = 'osfstorage'

MAX_ARCHIVE_SIZE = 5 * 1024 ** 3  # == math.pow(1024, 3) == 1 GB
MAX_FILE_SIZE = MAX_ARCHIVE_SIZE  # TODO limit file size?

ARCHIVE_TIMEOUT_TIMEDELTA = timedelta(1)  # 24 hours

ENABLE_ARCHIVER = True

JWT_SECRET = 'changeme'
JWT_ALGORITHM = 'HS256'

##### CELERY #####

DEFAULT_QUEUE = 'celery'
LOW_QUEUE = 'low'
MED_QUEUE = 'med'
HIGH_QUEUE = 'high'

LOW_PRI_MODULES = {
    'framework.analytics.tasks',
    'framework.celery_tasks',
    'scripts.osfstorage.usage_audit',
    'scripts.osfstorage.glacier_inventory',
    'scripts.analytics.tasks',
    'scripts.osfstorage.files_audit',
    'scripts.osfstorage.glacier_audit',
    'scripts.populate_new_and_noteworthy_projects',
    'website.search.elastic_search',
}

MED_PRI_MODULES = {
    'framework.email.tasks',
    'scripts.send_queued_mails',
    'scripts.triggered_mails',
    'website.mailchimp_utils',
    'website.notifications.tasks',
}

HIGH_PRI_MODULES = {
    'scripts.approve_embargo_terminations',
    'scripts.approve_registrations',
    'scripts.embargo_registrations',
    'scripts.refresh_addon_tokens',
    'scripts.retract_registrations',
    'website.archiver.tasks',
}

try:
    from kombu import Queue, Exchange
except ImportError:
    pass
else:
    CELERY_QUEUES = (
        Queue(LOW_QUEUE, Exchange(LOW_QUEUE), routing_key=LOW_QUEUE,
              consumer_arguments={'x-priority': -1}),
        Queue(DEFAULT_QUEUE, Exchange(DEFAULT_QUEUE), routing_key=DEFAULT_QUEUE,
              consumer_arguments={'x-priority': 0}),
        Queue(MED_QUEUE, Exchange(MED_QUEUE), routing_key=MED_QUEUE,
              consumer_arguments={'x-priority': 1}),
        Queue(HIGH_QUEUE, Exchange(HIGH_QUEUE), routing_key=HIGH_QUEUE,
              consumer_arguments={'x-priority': 10}),
    )

    CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
    CELERY_ROUTES = ('framework.celery_tasks.routers.CeleryRouter', )
    CELERY_IGNORE_RESULT = True
    CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True

# Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

# Modules to import when celery launches
CELERY_IMPORTS = (
    'framework.celery_tasks',
    'framework.celery_tasks.signals',
    'framework.email.tasks',
    'website.mailchimp_utils',
    'website.notifications.tasks',
    'website.archiver.tasks',
    'website.search.search',
    'website.project.tasks',
    'scripts.populate_new_and_noteworthy_projects',
    'scripts.refresh_addon_tokens',
    'scripts.retract_registrations',
    'scripts.embargo_registrations',
    'scripts.approve_registrations',
    'scripts.approve_embargo_terminations',
    'scripts.triggered_mails',
    'scripts.send_queued_mails',
)

# Modules that need metrics and release requirements
# CELERY_IMPORTS += (
#     'scripts.osfstorage.glacier_inventory',
#     'scripts.osfstorage.glacier_audit',
#     'scripts.osfstorage.usage_audit',
#     'scripts.osfstorage.files_audit',
#     'scripts.analytics.tasks',
#     'scripts.analytics.upload',
# )

# celery.schedule will not be installed when running invoke requirements the first time.
try:
    from celery.schedules import crontab
except ImportError:
    pass
else:
    #  Setting up a scheduler, essentially replaces an independent cron job
    CELERYBEAT_SCHEDULE = {
        '5-minute-emails': {
            'task': 'website.notifications.tasks.send_users_email',
            'schedule': crontab(minute='*/5'),
            'args': ('email_transactional',),
        },
        'daily-emails': {
            'task': 'website.notifications.tasks.send_users_email',
            'schedule': crontab(minute=0, hour=0),
            'args': ('email_digest',),
        },
        'refresh_addons': {
            'task': 'scripts.refresh_addon_tokens',
            'schedule': crontab(minute=0, hour= 2),  # Daily 2:00 a.m
            'kwargs': {'dry_run': False, 'addons': {'box': 60, 'googledrive': 14, 'mendeley': 14}},
        },
        'retract_registrations': {
            'task': 'scripts.retract_registrations',
            'schedule': crontab(minute=0, hour=0),  # Daily 12 a.m
            'kwargs': {'dry_run': False},
        },
        'embargo_registrations': {
            'task': 'scripts.embargo_registrations',
            'schedule': crontab(minute=0, hour=0),  # Daily 12 a.m
            'kwargs': {'dry_run': False},
        },
        'approve_registrations': {
            'task': 'scripts.approve_registrations',
            'schedule': crontab(minute=0, hour=0),  # Daily 12 a.m
            'kwargs': {'dry_run': False},
        },
        'approve_embargo_terminations': {
            'task': 'scripts.approve_embargo_terminations',
            'schedule': crontab(minute=0, hour=0),  # Daily 12 a.m
            'kwargs': {'dry_run': False},
        },
        'triggered_mails': {
            'task': 'scripts.triggered_mails',
            'schedule': crontab(minute=0, hour=0),  # Daily 12 a.m
            'kwargs': {'dry_run': False},
        },
        'send_queued_mails': {
            'task': 'scripts.send_queued_mails',
            'schedule': crontab(minute=0, hour=12),  # Daily 12 p.m.
            'kwargs': {'dry_run': False},
        },
        'new-and-noteworthy': {
            'task': 'scripts.populate_new_and_noteworthy_projects',
            'schedule': crontab(minute=0, hour=2, day_of_week=6),  # Saturday 2:00 a.m.
            'kwargs': {'dry_run': False}
        },
    }

    # Tasks that need metrics and release requirements
    # CELERYBEAT_SCHEDULE.update({
    #     'usage_audit': {
    #         'task': 'scripts.osfstorage.usage_audit',
    #         'schedule': crontab(minute=0, hour=0),  # Daily 12 a.m
    #         'kwargs': {'send_mail': True},
    #     },
    #     'glacier_inventory': {
    #         'task': 'scripts.osfstorage.glacier_inventory',
    #         'schedule': crontab(minute=0, hour= 0, day_of_week=0),  # Sunday 12:00 a.m.
    #         'args': (),
    #     },
    #     'glacier_audit': {
    #         'task': 'scripts.osfstorage.glacier_audit',
    #         'schedule': crontab(minute=0, hour=6, day_of_week=0),  # Sunday 6:00 a.m.
    #         'kwargs': {'dry_run': False},
    #     },
    #     'files_audit_0': {
    #         'task': 'scripts.osfstorage.files_audit.0',
    #         'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2:00 a.m.
    #         'kwargs': {'num_of_workers': 4, 'dry_run': False},
    #     },
    #     'files_audit_1': {
    #         'task': 'scripts.osfstorage.files_audit.1',
    #         'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2:00 a.m.
    #         'kwargs': {'num_of_workers': 4, 'dry_run': False},
    #     },
    #     'files_audit_2': {
    #         'task': 'scripts.osfstorage.files_audit.2',
    #         'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2:00 a.m.
    #         'kwargs': {'num_of_workers': 4, 'dry_run': False},
    #     },
    #     'files_audit_3': {
    #         'task': 'scripts.osfstorage.files_audit.3',
    #         'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2:00 a.m.
    #         'kwargs': {'num_of_workers': 4, 'dry_run': False},
    #     },
    #     'analytics': {
    #         'task': 'scripts.analytics.tasks',
    #         'schedule': crontab(minute=0, hour=2),  # Daily 2:00 a.m.
    #         'kwargs': {}
    #     },
    #     'analytics-upload': {
    #         'task': 'scripts.analytics.upload',
    #         'schedule': crontab(minute=0, hour=6),  # Daily 6:00 a.m.
    #         'kwargs': {}
    #     },
    # })


WATERBUTLER_JWE_SALT = 'yusaltydough'
WATERBUTLER_JWE_SECRET = 'CirclesAre4Squares'

WATERBUTLER_JWT_SECRET = 'ILiekTrianglesALot'
WATERBUTLER_JWT_ALGORITHM = 'HS256'
WATERBUTLER_JWT_EXPIRATION = 15

DRAFT_REGISTRATION_APPROVAL_PERIOD = datetime.timedelta(days=10)
assert (DRAFT_REGISTRATION_APPROVAL_PERIOD > EMBARGO_END_DATE_MIN), 'The draft registration approval period should be more than the minimum embargo end date.'

PREREG_ADMIN_TAG = "prereg_admin"

ENABLE_INSTITUTIONS = False

ENABLE_VARNISH = False
ENABLE_ESI = False
VARNISH_SERVERS = []  # This should be set in local.py or cache invalidation won't work
ESI_MEDIA_TYPES = {'application/vnd.api+json', 'application/json'}

# Used for gathering meta information about the current build
GITHUB_API_TOKEN = None

# External Identity Provider
EXTERNAL_IDENTITY_PROFILE = {
    'OrcidProfile': 'ORCID',
}

# Source: https://github.com/maxd/fake_email_validator/blob/master/config/fake_domains.list
BLACKLISTED_DOMAINS = [
    '0-mail.com',
    '0815.ru',
    '0815.su',
    '0clickemail.com',
    '0wnd.net',
    '0wnd.org',
    '10mail.org',
    '10minut.com.pl',
    '10minutemail.cf',
    '10minutemail.co.uk',
    '10minutemail.co.za',
    '10minutemail.com',
    '10minutemail.de',
    '10minutemail.eu',
    '10minutemail.ga',
    '10minutemail.gq',
    '10minutemail.info',
    '10minutemail.ml',
    '10minutemail.net',
    '10minutemail.org',
    '10minutemail.ru',
    '10minutemail.us',
    '10minutesmail.co.uk',
    '10minutesmail.com',
    '10minutesmail.eu',
    '10minutesmail.net',
    '10minutesmail.org',
    '10minutesmail.ru',
    '10minutesmail.us',
    '123-m.com',
    '15qm-mail.red',
    '15qm.com',
    '1chuan.com',
    '1mail.ml',
    '1pad.de',
    '1usemail.com',
    '1zhuan.com',
    '20mail.in',
    '20mail.it',
    '20minutemail.com',
    '2prong.com',
    '30minutemail.com',
    '30minutesmail.com',
    '33mail.com',
    '3d-painting.com',
    '3mail.ga',
    '4mail.cf',
    '4mail.ga',
    '4warding.com',
    '4warding.net',
    '4warding.org',
    '5mail.cf',
    '5mail.ga',
    '60minutemail.com',
    '675hosting.com',
    '675hosting.net',
    '675hosting.org',
    '6ip.us',
    '6mail.cf',
    '6mail.ga',
    '6mail.ml',
    '6paq.com',
    '6url.com',
    '75hosting.com',
    '75hosting.net',
    '75hosting.org',
    '7mail.ga',
    '7mail.ml',
    '7mail7.com',
    '7tags.com',
    '8mail.cf',
    '8mail.ga',
    '8mail.ml',
    '99experts.com',
    '9mail.cf',
    '9ox.net',
    'a-bc.net',
    'a45.in',
    'abcmail.email',
    'abusemail.de',
    'abyssmail.com',
    'acentri.com',
    'advantimo.com',
    'afrobacon.com',
    'agedmail.com',
    'ajaxapp.net',
    'alivance.com',
    'ama-trade.de',
    'amail.com',
    'amail4.me',
    'amilegit.com',
    'amiri.net',
    'amiriindustries.com',
    'anappthat.com',
    'ano-mail.net',
    'anobox.ru',
    'anonbox.net',
    'anonmails.de',
    'anonymail.dk',
    'anonymbox.com',
    'antichef.com',
    'antichef.net',
    'antireg.ru',
    'antispam.de',
    'antispammail.de',
    'appixie.com',
    'armyspy.com',
    'artman-conception.com',
    'asdasd.ru',
    'azmeil.tk',
    'baxomale.ht.cx',
    'beddly.com',
    'beefmilk.com',
    'beerolympics.se',
    'bestemailaddress.net',
    'bigprofessor.so',
    'bigstring.com',
    'binkmail.com',
    'bio-muesli.net',
    'bladesmail.net',
    'bloatbox.com',
    'bobmail.info',
    'bodhi.lawlita.com',
    'bofthew.com',
    'bootybay.de',
    'bossmail.de',
    'boun.cr',
    'bouncr.com',
    'boxformail.in',
    'boximail.com',
    'boxtemp.com.br',
    'breakthru.com',
    'brefmail.com',
    'brennendesreich.de',
    'broadbandninja.com',
    'bsnow.net',
    'bspamfree.org',
    'buffemail.com',
    'bugmenot.com',
    'bumpymail.com',
    'bund.us',
    'bundes-li.ga',
    'burnthespam.info',
    'burstmail.info',
    'buymoreplays.com',
    'buyusedlibrarybooks.org',
    'byom.de',
    'c2.hu',
    'cachedot.net',
    'card.zp.ua',
    'casualdx.com',
    'cbair.com',
    'cdnqa.com',
    'cek.pm',
    'cellurl.com',
    'cem.net',
    'centermail.com',
    'centermail.net',
    'chammy.info',
    'cheatmail.de',
    'chewiemail.com',
    'childsavetrust.org',
    'chogmail.com',
    'choicemail1.com',
    'chong-mail.com',
    'chong-mail.net',
    'chong-mail.org',
    'clixser.com',
    'clrmail.com',
    'cmail.net',
    'cmail.org',
    'coldemail.info',
    'consumerriot.com',
    'cool.fr.nf',
    'correo.blogos.net',
    'cosmorph.com',
    'courriel.fr.nf',
    'courrieltemporaire.com',
    'crapmail.org',
    'crazymailing.com',
    'cubiclink.com',
    'curryworld.de',
    'cust.in',
    'cuvox.de',
    'd3p.dk',
    'dacoolest.com',
    'daintly.com',
    'dandikmail.com',
    'dayrep.com',
    'dbunker.com',
    'dcemail.com',
    'deadaddress.com',
    'deadfake.cf',
    'deadfake.ga',
    'deadfake.ml',
    'deadfake.tk',
    'deadspam.com',
    'deagot.com',
    'dealja.com',
    'delikkt.de',
    'despam.it',
    'despammed.com',
    'devnullmail.com',
    'dfgh.net',
    'digitalsanctuary.com',
    'dingbone.com',
    'dingfone.com',
    'discard.cf',
    'discard.email',
    'discard.ga',
    'discard.gq',
    'discard.ml',
    'discard.tk',
    'discardmail.com',
    'discardmail.de',
    'dispomail.eu',
    'disposable-email.ml',
    'disposable.cf',
    'disposable.ga',
    'disposable.ml',
    'disposableaddress.com',
    'disposableemailaddresses.com',
    'disposableinbox.com',
    'dispose.it',
    'disposeamail.com',
    'disposemail.com',
    'dispostable.com',
    'divermail.com',
    'dodgeit.com',
    'dodgemail.de',
    'dodgit.com',
    'dodgit.org',
    'dodsi.com',
    'doiea.com',
    'domozmail.com',
    'donemail.ru',
    'dontmail.net',
    'dontreg.com',
    'dontsendmespam.de',
    'dotmsg.com',
    'drdrb.com',
    'drdrb.net',
    'droplar.com',
    'dropmail.me',
    'duam.net',
    'dudmail.com',
    'dump-email.info',
    'dumpandjunk.com',
    'dumpmail.de',
    'dumpyemail.com',
    'duskmail.com',
    'e-mail.com',
    'e-mail.org',
    'e4ward.com',
    'easytrashmail.com',
    'ee1.pl',
    'ee2.pl',
    'eelmail.com',
    'einmalmail.de',
    'einrot.com',
    'einrot.de',
    'eintagsmail.de',
    'email-fake.cf',
    'email-fake.com',
    'email-fake.ga',
    'email-fake.gq',
    'email-fake.ml',
    'email-fake.tk',
    'email60.com',
    'email64.com',
    'emailage.cf',
    'emailage.ga',
    'emailage.gq',
    'emailage.ml',
    'emailage.tk',
    'emaildienst.de',
    'emailgo.de',
    'emailias.com',
    'emailigo.de',
    'emailinfive.com',
    'emaillime.com',
    'emailmiser.com',
    'emailproxsy.com',
    'emails.ga',
    'emailsensei.com',
    'emailspam.cf',
    'emailspam.ga',
    'emailspam.gq',
    'emailspam.ml',
    'emailspam.tk',
    'emailtemporanea.com',
    'emailtemporanea.net',
    'emailtemporar.ro',
    'emailtemporario.com.br',
    'emailthe.net',
    'emailtmp.com',
    'emailto.de',
    'emailwarden.com',
    'emailx.at.hm',
    'emailxfer.com',
    'emailz.cf',
    'emailz.ga',
    'emailz.gq',
    'emailz.ml',
    'emeil.in',
    'emeil.ir',
    'emeraldwebmail.com',
    'emil.com',
    'emkei.cf',
    'emkei.ga',
    'emkei.gq',
    'emkei.ml',
    'emkei.tk',
    'emz.net',
    'enterto.com',
    'ephemail.net',
    'ero-tube.org',
    'etranquil.com',
    'etranquil.net',
    'etranquil.org',
    'evopo.com',
    'example.com',
    'explodemail.com',
    'express.net.ua',
    'eyepaste.com',
    'facebook-email.cf',
    'facebook-email.ga',
    'facebook-email.ml',
    'facebookmail.gq',
    'facebookmail.ml',
    'fake-box.com',
    'fake-mail.cf',
    'fake-mail.ga',
    'fake-mail.ml',
    'fakeinbox.cf',
    'fakeinbox.com',
    'fakeinbox.ga',
    'fakeinbox.ml',
    'fakeinbox.tk',
    'fakeinformation.com',
    'fakemail.fr',
    'fakemailgenerator.com',
    'fakemailz.com',
    'fammix.com',
    'fansworldwide.de',
    'fantasymail.de',
    'fastacura.com',
    'fastchevy.com',
    'fastchrysler.com',
    'fastkawasaki.com',
    'fastmazda.com',
    'fastmitsubishi.com',
    'fastnissan.com',
    'fastsubaru.com',
    'fastsuzuki.com',
    'fasttoyota.com',
    'fastyamaha.com',
    'fatflap.com',
    'fdfdsfds.com',
    'fightallspam.com',
    'fiifke.de',
    'filzmail.com',
    'fivemail.de',
    'fixmail.tk',
    'fizmail.com',
    'fleckens.hu',
    'flurre.com',
    'flurred.com',
    'flurred.ru',
    'flyspam.com',
    'footard.com',
    'forgetmail.com',
    'forward.cat',
    'fr33mail.info',
    'frapmail.com',
    'free-email.cf',
    'free-email.ga',
    'freemails.cf',
    'freemails.ga',
    'freemails.ml',
    'freundin.ru',
    'friendlymail.co.uk',
    'front14.org',
    'fuckingduh.com',
    'fudgerub.com',
    'fux0ringduh.com',
    'fyii.de',
    'garliclife.com',
    'gehensiemirnichtaufdensack.de',
    'gelitik.in',
    'germanmails.biz',
    'get-mail.cf',
    'get-mail.ga',
    'get-mail.ml',
    'get-mail.tk',
    'get1mail.com',
    'get2mail.fr',
    'getairmail.cf',
    'getairmail.com',
    'getairmail.ga',
    'getairmail.gq',
    'getairmail.ml',
    'getairmail.tk',
    'getmails.eu',
    'getonemail.com',
    'getonemail.net',
    'gfcom.com',
    'ghosttexter.de',
    'giantmail.de',
    'girlsundertheinfluence.com',
    'gishpuppy.com',
    'gmial.com',
    'goemailgo.com',
    'gorillaswithdirtyarmpits.com',
    'gotmail.com',
    'gotmail.net',
    'gotmail.org',
    'gowikibooks.com',
    'gowikicampus.com',
    'gowikicars.com',
    'gowikifilms.com',
    'gowikigames.com',
    'gowikimusic.com',
    'gowikinetwork.com',
    'gowikitravel.com',
    'gowikitv.com',
    'grandmamail.com',
    'grandmasmail.com',
    'great-host.in',
    'greensloth.com',
    'grr.la',
    'gsrv.co.uk',
    'guerillamail.biz',
    'guerillamail.com',
    'guerillamail.de',
    'guerillamail.net',
    'guerillamail.org',
    'guerillamailblock.com',
    'guerrillamail.biz',
    'guerrillamail.com',
    'guerrillamail.de',
    'guerrillamail.info',
    'guerrillamail.net',
    'guerrillamail.org',
    'guerrillamailblock.com',
    'gustr.com',
    'h8s.org',
    'hacccc.com',
    'haltospam.com',
    'haqed.com',
    'harakirimail.com',
    'hartbot.de',
    'hat-geld.de',
    'hatespam.org',
    'headstrong.de',
    'hellodream.mobi',
    'herp.in',
    'hidemail.de',
    'hideme.be',
    'hidzz.com',
    'hiru-dea.com',
    'hmamail.com',
    'hochsitze.com',
    'hopemail.biz',
    'hot-mail.cf',
    'hot-mail.ga',
    'hot-mail.gq',
    'hot-mail.ml',
    'hot-mail.tk',
    'hotpop.com',
    'hulapla.de',
    'hushmail.com',
    'ieatspam.eu',
    'ieatspam.info',
    'ieh-mail.de',
    'ihateyoualot.info',
    'iheartspam.org',
    'ikbenspamvrij.nl',
    'imails.info',
    'imgof.com',
    'imgv.de',
    'imstations.com',
    'inbax.tk',
    'inbox.si',
    'inboxalias.com',
    'inboxclean.com',
    'inboxclean.org',
    'inboxproxy.com',
    'incognitomail.com',
    'incognitomail.net',
    'incognitomail.org',
    'ineec.net',
    'infocom.zp.ua',
    'inoutmail.de',
    'inoutmail.eu',
    'inoutmail.info',
    'inoutmail.net',
    'insorg-mail.info',
    'instant-mail.de',
    'instantemailaddress.com',
    'instantlyemail.com',
    'ip6.li',
    'ipoo.org',
    'irish2me.com',
    'iwi.net',
    'jetable.com',
    'jetable.fr.nf',
    'jetable.net',
    'jetable.org',
    'jnxjn.com',
    'jourrapide.com',
    'junk1e.com',
    'junkmail.com',
    'junkmail.ga',
    'junkmail.gq',
    'jupimail.com',
    'kasmail.com',
    'kaspop.com',
    'keepmymail.com',
    'killmail.com',
    'killmail.net',
    'kimsdisk.com',
    'kingsq.ga',
    'kiois.com',
    'kir.ch.tc',
    'klassmaster.com',
    'klassmaster.net',
    'klzlk.com',
    'kook.ml',
    'koszmail.pl',
    'kulturbetrieb.info',
    'kurzepost.de',
    'l33r.eu',
    'labetteraverouge.at',
    'lackmail.net',
    'lags.us',
    'landmail.co',
    'lastmail.co',
    'lawlita.com',
    'lazyinbox.com',
    'legitmail.club',
    'letthemeatspam.com',
    'lhsdv.com',
    'libox.fr',
    'lifebyfood.com',
    'link2mail.net',
    'litedrop.com',
    'loadby.us',
    'login-email.cf',
    'login-email.ga',
    'login-email.ml',
    'login-email.tk',
    'lol.ovpn.to',
    'lolfreak.net',
    'lookugly.com',
    'lopl.co.cc',
    'lortemail.dk',
    'lovemeleaveme.com',
    'lr78.com',
    'lroid.com',
    'lukop.dk',
    'm21.cc',
    'm4ilweb.info',
    'maboard.com',
    'mail-filter.com',
    'mail-temporaire.fr',
    'mail.by',
    'mail.mezimages.net',
    'mail.zp.ua',
    'mail114.net',
    'mail1a.de',
    'mail21.cc',
    'mail2rss.org',
    'mail333.com',
    'mail4trash.com',
    'mailbidon.com',
    'mailbiz.biz',
    'mailblocks.com',
    'mailblog.biz',
    'mailbucket.org',
    'mailcat.biz',
    'mailcatch.com',
    'mailde.de',
    'mailde.info',
    'maildrop.cc',
    'maildrop.cf',
    'maildrop.ga',
    'maildrop.gq',
    'maildrop.ml',
    'maildu.de',
    'maildx.com',
    'maileater.com',
    'mailed.ro',
    'maileimer.de',
    'mailexpire.com',
    'mailfa.tk',
    'mailforspam.com',
    'mailfree.ga',
    'mailfree.gq',
    'mailfree.ml',
    'mailfreeonline.com',
    'mailfs.com',
    'mailguard.me',
    'mailhazard.com',
    'mailhazard.us',
    'mailhz.me',
    'mailimate.com',
    'mailin8r.com',
    'mailinater.com',
    'mailinator.com',
    'mailinator.gq',
    'mailinator.net',
    'mailinator.org',
    'mailinator.us',
    'mailinator2.com',
    'mailinator2.net',
    'mailincubator.com',
    'mailismagic.com',
    'mailjunk.cf',
    'mailjunk.ga',
    'mailjunk.gq',
    'mailjunk.ml',
    'mailjunk.tk',
    'mailmate.com',
    'mailme.gq',
    'mailme.ir',
    'mailme.lv',
    'mailme24.com',
    'mailmetrash.com',
    'mailmoat.com',
    'mailms.com',
    'mailnator.com',
    'mailnesia.com',
    'mailnull.com',
    'mailorg.org',
    'mailpick.biz',
    'mailproxsy.com',
    'mailquack.com',
    'mailrock.biz',
    'mailscrap.com',
    'mailshell.com',
    'mailsiphon.com',
    'mailslapping.com',
    'mailslite.com',
    'mailspeed.ru',
    'mailtemp.info',
    'mailtome.de',
    'mailtothis.com',
    'mailtrash.net',
    'mailtv.net',
    'mailtv.tv',
    'mailzilla.com',
    'mailzilla.org',
    'mailzilla.orgmbx.cc',
    'makemetheking.com',
    'mallinator.com',
    'manifestgenerator.com',
    'manybrain.com',
    'mbx.cc',
    'mciek.com',
    'mega.zik.dj',
    'meinspamschutz.de',
    'meltmail.com',
    'messagebeamer.de',
    'mezimages.net',
    'mfsa.ru',
    'mierdamail.com',
    'migmail.pl',
    'migumail.com',
    'mindless.com',
    'ministry-of-silly-walks.de',
    'mintemail.com',
    'misterpinball.de',
    'mjukglass.nu',
    'moakt.com',
    'mobi.web.id',
    'mobileninja.co.uk',
    'moburl.com',
    'mohmal.com',
    'moncourrier.fr.nf',
    'monemail.fr.nf',
    'monmail.fr.nf',
    'monumentmail.com',
    'msa.minsmail.com',
    'mt2009.com',
    'mt2014.com',
    'mt2015.com',
    'mx0.wwwnew.eu',
    'my10minutemail.com',
    'myalias.pw',
    'mycard.net.ua',
    'mycleaninbox.net',
    'myemailboxy.com',
    'mymail-in.net',
    'mymailoasis.com',
    'mynetstore.de',
    'mypacks.net',
    'mypartyclip.de',
    'myphantomemail.com',
    'mysamp.de',
    'myspaceinc.com',
    'myspaceinc.net',
    'myspaceinc.org',
    'myspacepimpedup.com',
    'myspamless.com',
    'mytemp.email',
    'mytempemail.com',
    'mytempmail.com',
    'mytrashmail.com',
    'nabuma.com',
    'neomailbox.com',
    'nepwk.com',
    'nervmich.net',
    'nervtmich.net',
    'netmails.com',
    'netmails.net',
    'netzidiot.de',
    'neverbox.com',
    'nice-4u.com',
    'nincsmail.com',
    'nincsmail.hu',
    'nmail.cf',
    'nnh.com',
    'no-spam.ws',
    'noblepioneer.com',
    'nobulk.com',
    'noclickemail.com',
    'nogmailspam.info',
    'nomail.pw',
    'nomail.xl.cx',
    'nomail2me.com',
    'nomorespamemails.com',
    'nonspam.eu',
    'nonspammer.de',
    'noref.in',
    'nospam.ze.tc',
    'nospam4.us',
    'nospamfor.us',
    'nospammail.net',
    'nospamthanks.info',
    'notmailinator.com',
    'notsharingmy.info',
    'nowhere.org',
    'nowmymail.com',
    'nurfuerspam.de',
    'nus.edu.sg',
    'nwldx.com',
    'objectmail.com',
    'obobbo.com',
    'odaymail.com',
    'odnorazovoe.ru',
    'one-time.email',
    'oneoffemail.com',
    'oneoffmail.com',
    'onewaymail.com',
    'onlatedotcom.info',
    'online.ms',
    'oopi.org',
    'opayq.com',
    'opentrash.com',
    'ordinaryamerican.net',
    'otherinbox.com',
    'ourklips.com',
    'outlawspam.com',
    'ovpn.to',
    'owlpic.com',
    'pancakemail.com',
    'paplease.com',
    'pepbot.com',
    'pfui.ru',
    'pimpedupmyspace.com',
    'pjjkp.com',
    'plexolan.de',
    'poczta.onet.pl',
    'politikerclub.de',
    'poofy.org',
    'pookmail.com',
    'pop3.xyz',
    'postalmail.biz',
    'privacy.net',
    'privatdemail.net',
    'privy-mail.com',
    'privymail.de',
    'proxymail.eu',
    'prtnx.com',
    'prtz.eu',
    'pubmail.io',
    'punkass.com',
    'putthisinyourspamdatabase.com',
    'pwrby.com',
    'q314.net',
    'qisdo.com',
    'qisoa.com',
    'qoika.com',
    'qq.com',
    'quickinbox.com',
    'quickmail.nl',
    'rainmail.biz',
    'rcpt.at',
    're-gister.com',
    'reallymymail.com',
    'realtyalerts.ca',
    'recode.me',
    'reconmail.com',
    'recursor.net',
    'recyclemail.dk',
    'regbypass.com',
    'regbypass.comsafe-mail.net',
    'rejectmail.com',
    'reliable-mail.com',
    'remail.cf',
    'remail.ga',
    'renraku.in',
    'rhyta.com',
    'rklips.com',
    'rmqkr.net',
    'royal.net',
    'rppkn.com',
    'rtrtr.com',
    's0ny.net',
    'safe-mail.net',
    'safersignup.de',
    'safetymail.info',
    'safetypost.de',
    'sandelf.de',
    'sayawaka-dea.info',
    'saynotospams.com',
    'scatmail.com',
    'schafmail.de',
    'schrott-email.de',
    'secretemail.de',
    'secure-mail.biz',
    'secure-mail.cc',
    'selfdestructingmail.com',
    'selfdestructingmail.org',
    'sendspamhere.com',
    'senseless-entertainment.com',
    'services391.com',
    'sharedmailbox.org',
    'sharklasers.com',
    'shieldedmail.com',
    'shieldemail.com',
    'shiftmail.com',
    'shitmail.me',
    'shitmail.org',
    'shitware.nl',
    'shmeriously.com',
    'shortmail.net',
    'showslow.de',
    'sibmail.com',
    'sinnlos-mail.de',
    'siteposter.net',
    'skeefmail.com',
    'slapsfromlastnight.com',
    'slaskpost.se',
    'slipry.net',
    'slopsbox.com',
    'slowslow.de',
    'slushmail.com',
    'smashmail.de',
    'smellfear.com',
    'smellrear.com',
    'smoug.net',
    'snakemail.com',
    'sneakemail.com',
    'sneakmail.de',
    'snkmail.com',
    'sofimail.com',
    'sofort-mail.de',
    'softpls.asia',
    'sogetthis.com',
    'soisz.com',
    'solvemail.info',
    'soodonims.com',
    'spam.la',
    'spam.su',
    'spam4.me',
    'spamail.de',
    'spamarrest.com',
    'spamavert.com',
    'spambob.com',
    'spambob.net',
    'spambob.org',
    'spambog.com',
    'spambog.de',
    'spambog.net',
    'spambog.ru',
    'spambooger.com',
    'spambox.info',
    'spambox.irishspringrealty.com',
    'spambox.us',
    'spambpg.com',
    'spamcannon.com',
    'spamcannon.net',
    'spamcero.com',
    'spamcon.org',
    'spamcorptastic.com',
    'spamcowboy.com',
    'spamcowboy.net',
    'spamcowboy.org',
    'spamday.com',
    'spamex.com',
    'spamfighter.cf',
    'spamfighter.ga',
    'spamfighter.gq',
    'spamfighter.ml',
    'spamfighter.tk',
    'spamfree.eu',
    'spamfree24.com',
    'spamfree24.de',
    'spamfree24.eu',
    'spamfree24.info',
    'spamfree24.net',
    'spamfree24.org',
    'spamgoes.in',
    'spamgourmet.com',
    'spamgourmet.net',
    'spamgourmet.org',
    'spamherelots.com',
    'spamhereplease.com',
    'spamhole.com',
    'spamify.com',
    'spaminator.de',
    'spamkill.info',
    'spaml.com',
    'spaml.de',
    'spammotel.com',
    'spamobox.com',
    'spamoff.de',
    'spamsalad.in',
    'spamslicer.com',
    'spamsphere.com',
    'spamspot.com',
    'spamstack.net',
    'spamthis.co.uk',
    'spamthisplease.com',
    'spamtrail.com',
    'spamtroll.net',
    'speed.1s.fr',
    'spikio.com',
    'spoofmail.de',
    'spybox.de',
    'squizzy.de',
    'ssoia.com',
    'startkeys.com',
    'stexsy.com',
    'stinkefinger.net',
    'stop-my-spam.cf',
    'stop-my-spam.com',
    'stop-my-spam.ga',
    'stop-my-spam.ml',
    'stop-my-spam.tk',
    'streetwisemail.com',
    'stuffmail.de',
    'super-auswahl.de',
    'supergreatmail.com',
    'supermailer.jp',
    'superrito.com',
    'superstachel.de',
    'suremail.info',
    'sute.jp',
    'svk.jp',
    'sweetxxx.de',
    'tafmail.com',
    'tagyourself.com',
    'talkinator.com',
    'tapchicuoihoi.com',
    'teewars.org',
    'teleworm.com',
    'teleworm.us',
    'temp-mail.com',
    'temp-mail.net',
    'temp-mail.org',
    'temp-mail.ru',
    'temp15qm.com',
    'tempail.com',
    'tempalias.com',
    'tempe-mail.com',
    'tempemail.biz',
    'tempemail.co.za',
    'tempemail.com',
    'tempemail.net',
    'tempemail.org',
    'tempinbox.co.uk',
    'tempinbox.com',
    'tempmail.de',
    'tempmail.eu',
    'tempmail.it',
    'tempmail2.com',
    'tempmaildemo.com',
    'tempmailer.com',
    'tempmailer.de',
    'tempomail.fr',
    'temporarily.de',
    'temporarioemail.com.br',
    'temporaryemail.net',
    'temporaryemail.us',
    'temporaryforwarding.com',
    'temporaryinbox.com',
    'temporarymailaddress.com',
    'tempsky.com',
    'tempthe.net',
    'tempymail.com',
    'test.com',
    'thanksnospam.info',
    'thankyou2010.com',
    'thc.st',
    'thecloudindex.com',
    'thisisnotmyrealemail.com',
    'thismail.net',
    'thismail.ru',
    'throam.com',
    'throwam.com',
    'throwawayemailaddress.com',
    'throwawaymail.com',
    'tilien.com',
    'tittbit.in',
    'tizi.com',
    'tmail.ws',
    'tmailinator.com',
    'tmpeml.info',
    'toiea.com',
    'tokenmail.de',
    'toomail.biz',
    'topranklist.de',
    'tormail.net',
    'tormail.org',
    'tradermail.info',
    'trash-amil.com',
    'trash-mail.at',
    'trash-mail.cf',
    'trash-mail.com',
    'trash-mail.de',
    'trash-mail.ga',
    'trash-mail.gq',
    'trash-mail.ml',
    'trash-mail.tk',
    'trash-me.com',
    'trash2009.com',
    'trash2010.com',
    'trash2011.com',
    'trashdevil.com',
    'trashdevil.de',
    'trashemail.de',
    'trashmail.at',
    'trashmail.com',
    'trashmail.de',
    'trashmail.me',
    'trashmail.net',
    'trashmail.org',
    'trashmail.ws',
    'trashmailer.com',
    'trashymail.com',
    'trashymail.net',
    'trayna.com',
    'trbvm.com',
    'trialmail.de',
    'trickmail.net',
    'trillianpro.com',
    'tryalert.com',
    'turual.com',
    'twinmail.de',
    'twoweirdtricks.com',
    'tyldd.com',
    'ubismail.net',
    'uggsrock.com',
    'umail.net',
    'unlimit.com',
    'unmail.ru',
    'upliftnow.com',
    'uplipht.com',
    'uroid.com',
    'us.af',
    'valemail.net',
    'venompen.com',
    'vermutlich.net',
    'veryrealemail.com',
    'vidchart.com',
    'viditag.com',
    'viewcastmedia.com',
    'viewcastmedia.net',
    'viewcastmedia.org',
    'viralplays.com',
    'vmail.me',
    'voidbay.com',
    'vomoto.com',
    'vpn.st',
    'vsimcard.com',
    'vubby.com',
    'w3internet.co.uk',
    'walala.org',
    'walkmail.net',
    'watchever.biz',
    'webemail.me',
    'webm4il.info',
    'webuser.in',
    'wee.my',
    'weg-werf-email.de',
    'wegwerf-email-addressen.de',
    'wegwerf-email.at',
    'wegwerf-emails.de',
    'wegwerfadresse.de',
    'wegwerfemail.com',
    'wegwerfemail.de',
    'wegwerfmail.de',
    'wegwerfmail.info',
    'wegwerfmail.net',
    'wegwerfmail.org',
    'wem.com',
    'wetrainbayarea.com',
    'wetrainbayarea.org',
    'wh4f.org',
    'whatiaas.com',
    'whatpaas.com',
    'whatsaas.com',
    'whopy.com',
    'whyspam.me',
    'wickmail.net',
    'wilemail.com',
    'willhackforfood.biz',
    'willselfdestruct.com',
    'winemaven.info',
    'wmail.cf',
    'writeme.com',
    'wronghead.com',
    'wuzup.net',
    'wuzupmail.net',
    'wwwnew.eu',
    'wzukltd.com',
    'xagloo.com',
    'xemaps.com',
    'xents.com',
    'xmaily.com',
    'xoxy.net',
    'xww.ro',
    'xyzfree.net',
    'yapped.net',
    'yep.it',
    'yogamaven.com',
    'yomail.info',
    'yopmail.com',
    'yopmail.fr',
    'yopmail.gq',
    'yopmail.net',
    'yopmail.org',
    'yoru-dea.com',
    'you-spam.com',
    'youmail.ga',
    'yourdomain.com',
    'ypmail.webarnak.fr.eu.org',
    'yuurok.com',
    'yyhmail.com',
    'z1p.biz',
    'za.com',
    'zebins.com',
    'zebins.eu',
    'zehnminuten.de',
    'zehnminutenmail.de',
    'zetmail.com',
    'zippymail.info',
    'zoaxe.com',
    'zoemail.com',
    'zoemail.net',
    'zoemail.org',
    'zomg.info',
    'zxcv.com',
    'zxcvbnm.com',
    'zzz.com',
]

# reCAPTCHA API
RECAPTCHA_SITE_KEY = None
RECAPTCHA_SECRET_KEY = None
RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

# akismet spam check
AKISMET_APIKEY = None
SPAM_CHECK_ENABLED = False
SPAM_CHECK_PUBLIC_ONLY = True
SPAM_ACCOUNT_SUSPENSION_ENABLED = False
SPAM_ACCOUNT_SUSPENSION_THRESHOLD = timedelta(hours=24)
SPAM_FLAGGED_MAKE_NODE_PRIVATE = False
SPAM_FLAGGED_REMOVE_FROM_SEARCH = False

SHARE_URL = 'http://localhost:8000/'
SHARE_API_TOKEN = None
