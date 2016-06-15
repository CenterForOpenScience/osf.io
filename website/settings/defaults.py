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

# Hours before email confirmation tokens expire
EMAIL_TOKEN_EXPIRATION = 24
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

LOAD_BALANCER = False
PROXY_ADDRS = []

# May set these to True in local.py for development
DEV_MODE = False
DEBUG_MODE = False

LOG_PATH = os.path.join(APP_PATH, 'logs')
TEMPLATES_PATH = os.path.join(BASE_PATH, 'templates')
ANALYTICS_PATH = os.path.join(BASE_PATH, 'analytics')

CORE_TEMPLATES = os.path.join(BASE_PATH, 'templates/log_templates.mako')
BUILT_TEMPLATES = os.path.join(BASE_PATH, 'templates/_log_templates.mako')

DOMAIN = 'http://localhost:5000/'
API_DOMAIN = 'http://localhost:8000/'
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
SHARE_ELASTIC_URI = ELASTIC_URI
SHARE_ELASTIC_INDEX = 'share'
# For old indices
SHARE_ELASTIC_INDEX_TEMPLATE = 'share_v{}'

# Sessions
# TODO: Override OSF_COOKIE_DOMAIN in local.py in production
OSF_COOKIE_DOMAIN = None
COOKIE_NAME = 'osf'
# server-side verification timeout
OSF_SESSION_TIMEOUT = 30 * 24 * 60 * 60  # 30 days in seconds
# TODO: Override SECRET_KEY in local.py in production
SECRET_KEY = 'CHANGEME'

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

# Add-ons
# Load addons from addons.json
with open(os.path.join(ROOT, 'addons.json')) as fp:
    addon_settings = json.load(fp)
    ADDONS_REQUESTED = addon_settings['addons']
    ADDONS_ARCHIVABLE = addon_settings['addons_archivable']
    ADDONS_COMMENTABLE = addon_settings['addons_commentable']
    ADDONS_BASED_ON_IDS = addon_settings['addons_based_on_ids']

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

# Piwik

# TODO: Override in local.py in production
PIWIK_HOST = None
PIWIK_ADMIN_TOKEN = None
PIWIK_SITE_ID = None

KEEN_PROJECT_ID = None
KEEN_WRITE_KEY = None
KEEN_READ_KEY = None

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


USE_SHARE = True
SHARE_REGISTRATION_URL = ''
SHARE_API_DOCS_URL = ''

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

# Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

# Modules to import when celery launches
CELERY_IMPORTS = (
    'framework.celery_tasks',
    'framework.celery_tasks.signals',
    'framework.email.tasks',
    'framework.analytics.tasks',
    'website.mailchimp_utils',
    'website.notifications.tasks',
    'website.archiver.tasks',
    'website.search.search',
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

DISCOURSE_SSO_SECRET = 'changeme'
DISCOURSE_SERVER_URL = 'http://192.168.99.100'
DISCOURSE_API_KEY = 'changeme'
DISCOURSE_API_ADMIN_USER = 'changeme'

DISCOURSE_SERVER_SETTINGS = {'title': 'Open Science Framework',
                             'site_description': 'A scholarly commons to connect the entire research cycle',
                             'contact_email': 'changeme',
                             'contact_url': '',
                             'notification_email': 'noreply@osf.io',
                             'site_contact_username': 'system',
                             'logo_url': '',
                             'logo_small_url': '',
                             'favicon_url': DOMAIN + 'favicon.ico',
                             'enable_local_logins': 'false',
                             'enable_sso': 'true',
                             'sso_url': API_DOMAIN + 'v2/sso',
                             'sso_secret': DISCOURSE_SSO_SECRET,
                             'sso_overrides_email': 'true',
                             'sso_overrides_username': 'true',
                             'sso_overrides_name': 'true',
                             'sso_overrides_avatar': 'true',
                             'logout_redirect': DOMAIN + 'logout',
                             'cors_origins': DOMAIN,
                             'min_topic_title_length': '0',
                             'title_min_entropy': '0',
                             'title_prettify': 'false',
                             'allow_duplicate_topic_titles': 'true',
                             'tagging_enabled': 'true',
                             }

DISCOURSE_SERVER_CUSTOMIZATIONS = [{'name': 'MFR',
                                    'enabled': 'true',
                                    'head_tag': '<link href="https://mfr.osf.io/static/css/mfr.css" media="all" rel="stylesheet">',
                                    'body_tag': '''
<style>
    #mfrIframe {
        width: 100%:
    }
</style>

<script src="https://mfr.osf.io/static/js/mfr.js"></script>
<script>
var observeDOM = (function(){
    var MutationObserver = window.MutationObserver || window.WebKitMutationObserver,
        eventListenerSupported = window.addEventListener;

    return function(obj, callback){
        if( MutationObserver ){
            // define a new observer
            var obs = new MutationObserver(function(mutations, observer){
                if( mutations[0].addedNodes.length || mutations[0].removedNodes.length )
                    callback();
            });
            // have the observer observe foo for changes in children
            obs.observe( obj, { childList:true, subtree:true });
        }
    }
})();

// Observe a specific DOM element:
observeDOM(document.body, function() {

    var topic_post = document.querySelector('.topic-post article#post_1 .cooked');

    if (!topic_post) return;
    if (document.getElementById("mfrIframe")) return;

    var mfr_div = document.createElement('div');
    mfr_div.id = "mfrIframe";
    mfr_div.classList.add('mfr', 'mrf-file');
    var reg = new RegExp('\:\/\/(?:osf|local)[^\/]*\/([a-z0-9]*)\/?');
    var match = reg.exec(topic_post.textContent)
    if (match) {
        var guid = match[1];
        topic_post.appendChild(mfr_div);
        window.jQuery || document.write('<script src="//code.jquery.com/jquery-1.11.2.min.js">\\x3C/script>');
        var mfrRender = new mfr.Render("mfrIframe", "''' + MFR_SERVER_URL + '''/render?url=''' + DOMAIN + '''"+guid+"/?action=download%26mode=render");
    }
});


</script>
                                    ''',
                                    },
                                   {'name': 'Embedded Comments',
                                    'enabled': 'true',
                                    'embedded_css': '''
body {
    background: whitesmoke;
    font-family: 'Open Sans', 'Helvetica Neue', sans-serif;
	font-style: normal;
	font-variant: normal;
	font-weight: 200;
	    -webkit-font-smoothing: antialiased;
}

a:hover {
    color: #204762;
}

.username .staff {
    background-color: whitesmoke;
}

.username a {
    color: #337ab7 ;
}

.username a:hover {
    color: #204762;
}

footer .button {
    background-color: whitesmoke ;
    color: #337ab7 ;
}

footer a:hover {
    color: #204762;
}
                                    ''',
                                   },
                                   {'name': 'Title Manager',
                                    'enabled': 'true',
                                    'body_tag': '''
<script>(function(){

var observeDOM = (function(){
    var MutationObserver = window.MutationObserver || window.WebKitMutationObserver,
        eventListenerSupported = window.addEventListener;

    return function(obj, callback){
        if( MutationObserver ){
            // define a new observer
            var obs = new MutationObserver(function(mutations, observer){
                if( mutations[0].addedNodes.length || mutations[0].removedNodes.length )
                    callback();
            });
            // have the observer observe foo for changes in children
            obs.observe( obj, { childList:true, subtree:true });
        }
    }
})();

// Observe a specific DOM element:
observeDOM(document.body, function() {
    console.log('mutation!')

    var embedded_title = document.querySelector('.topic-post article#post_1 .cooked code');
    if (!embedded_title) return;
    console.log('got topic post')

    var topic_title = document.querySelector('#topic-title .title-wrapper .fancy-title')
    if (!topic_title || topic_title.classList.contains('hacked')) return;
    console.log('got topic title');

    topic_title.innerHTML = embedded_title.textContent;
    console.log(embedded_title);
    console.log(embedded_title.parentNode)
    embedded_title.parentNode.removeChild(embedded_title)
    topic_title.classList.add('hacked')
});

})()</script>
                                    ''',
                                   },
                                  {'name': 'Top Header',
                                   'enabled': 'true',
                                   'stylesheet': '''
/********** Sticky Nav **********/

a {

font-family: 'Helvetica Neue', Helvetica, Arial, Utkal, sans-serif;
font-weight: 300;
}

section.ember-application {
    padding-top: 0;
}

.desktop-view body .ember-view > header.d-header {
    position: fixed;
    top: 0;
    background-color: #263947;

}
.title a:after {
    margin-left: 10px;
    font-size: 24px;
    content: "Open Science Framework";
    font-family: 'Open Sans', 'Helvetica Neue', sans-serif;

    &:hover {
        color: #e0ebf3;
      }
-webkit-font-smoothing: antialiased;
}

.desktop-view body #main {
  padding-top: 74px;
}

#top-navbar {
  height:60px;
  background-color:#263947;
  width:100%;
  position: fixed;
  z-index: 1001;
}

.desktop-view body header.d-header {
  top: 59px;
  padding-top: 6px;
}

div#top-navbar-links {
  width:100%;
  margin: 0 auto;
  padding-top: 0;
  max-width:1100px;
  margin-top: 0;
}

div#top-navbar-links a, div#top-navbar-links span {
  color:#eee;
  font-size: 14px;
}

div.cos-icon--main {
    float: left;
    margin-right: 10px;

    > a, > a:visited, > a:active {
      display: inline-block;
      padding: 6px 10px;
      font-size: 14px;
      color: #eeeeee;

      &:hover {
        color: #e0ebf3;
      }
    }
  }

.navbar-brand {
    float: left;
    padding: 12.5px 15px ;
    font-size: 18px;
    line-height: 25px;
    height: 50px ;
}

/* js dropdown navs */
#top-external-nav {
  float: right;
  margin-top: 12px;
  position: right;
  list-style: none;

  li.top-ext--main {
    float: left;
    position: relative;
    margin-right: 10px;
    > a, > a:visited, > a:active {
      display: inline-block;
      padding: 6px 10px;
      font-size: 14px;
      color: #eeeeee;
      &:hover {
        color: #e0ebf3;
      }
    }
  }

  #top-discourse-link a.top-discourse-link-main {
    padding: 6px 10px 20px 10px;
  }

  ul.top-ext--sub {
    display: none;
    position: absolute;
    top: 40px;
    left: 0;
    margin-left: 0;
    background-color: white;
    box-shadow: 0 2px 5px rgba(0,0,0, .5);
    list-style: none;

    li.top-ext--sub-item {
      float: none;
      padding: 0;
      margin: 0;
      background-color: white;
      a, a:visited {
        display: inline-block;
        width: 190px;
        padding: 8px 10px;
        span {
          font-size: 14px;
          color: #666;
        }

        img {
          width: 20px;
          margin-right: 6px;
        }
      }

      &:hover {
        background-color: #eef;
      }
    }
  }
}
                                ''',
                                'header': '''
<!DOCTYPE html>

    <div id="top-navbar" style='display:none;'>
      <div id="top-navbar-links">
          <div class="cos-icon--main">
            <a class="navbar-brand hidden-sm hidden-xs" href="/" >
                <img src="http://discourse.mechanysm.com/uploads/default/original/1X/0ea2d6e023b73a218200bded19cec4b95c58e667.png" class="cos-icon--main" width="27" alt="COS">
                "Open Science Framework"
            </a>
          </div>
        <div class="panel clearfix">
            <ul id="top-external-nav" class="icons clearfix">

              <li class="top-ext--main">
                <a class="top-ext--link" href="http://osf.io/" target="blank">Dashboard</a>
              </li>

              <li class="top-ext--main">
                <a class="top-ext--link" href="https://osf.io/myprojects/" target="blank">My Project</a>
              </li>

              <li class="top-ext--main" id="top-discourse-link">
               ; <a class="top-ext--link top-discourse-link-main">Browse</a>
                <ul class="top-ext--sub" id="top-discourse-sub">
                  <li class="top-ext--sub-item">
                    <a class="top-ext--link" href="https://osf.io/explore/activity/" target="blank">
                      <span>New Project</span>
                    </a>
                  </li>
                  <li class="top-ext--sub-item">
                    <a class="top-ext--link" href="" target="blank">
                      <span>Registry</span>
                    </a>
                  </li>
                  <li class="top-ext--sub-item">
                    <a class="top-ext--link" href="https://osf.io/meetings/" target="blank">
                      <span>Meetings</span>
                    </a>
                  </li>
                </ul>
              </li>
            </ul>
        </div>
      </div>
    </div>
                                   ''',
                                   'head_tag': '''
<!DOCTYPE html>
<link href='https://fonts.googleapis.com/css?family=Open+Sans:400,300' rel='stylesheet' type='text/css'>
<script type="text/javascript">

$(function() {
  var $topDiscourseSub = $('#top-discourse-sub');
  $('#top-discourse-link').hover(function() {
    $topDiscourseSub.show();
  }, function() {
    $topDiscourseSub.hide();
  });
});
</script>
                                   ''',
                                  },
                                 {'name': 'Topic Header',
                                  'enabled': 'true',
                                  'head_tag': '',
                                  'body_tag': '''
<style>
    #project_header {
        background-color: #eee;
        box-shadow: 0 3 10px 10px rgba(0,0,0,0.4);
        overflow: hidden;
    }
    #project_header > ul > li {
        float: left;
        list-style-type: none;
        padding: 10px;
        color: #337ab7;
    }
    #project_header > ul > li:hover {
        background-color: #e1e1e1;
        color: #337;
    }
</style>
<script>
// Observe a specific DOM element:
observeDOM(document.body, function() {
    var discourse_header = document.querySelector('header.d-header');
    var topic_post = document.querySelector('.topic-post article#post_1 .cooked');

    if (!discourse_header) return;
    if (!topic_post) return;
    if (document.getElementById("project_header")) return;

    var project_header = document.createElement('div');
    project_header.id = "project_header";

    var ul = document.createElement('ul');
    ul.classList.add("wrap");
    ul.style.margin = "0 auto";

    [
        "Project",
        "Files",
        "Wiki",
        "Analytics",
        "Registrations",
        "Forks"
    ].map(function(x) {
        var li = document.createElement("li");
        li.textContent = x
        ul.appendChild(li);
    });

    project_header.appendChild(ul);
    discourse_header.appendChild(project_header);
});
</script>
                                  ''',
                                 }]
