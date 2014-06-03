# -*- coding: utf-8 -*-
"""
Base settings file, common to all environments.
These settings can be overridden in local.py.
"""

import os

def parent_dir(path):
    '''Return the parent of a directory.'''
    return os.path.abspath(os.path.join(path, os.pardir))

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = parent_dir(HERE)  # website/ directory
STATIC_FOLDER = os.path.join(BASE_PATH, 'static')
STATIC_URL_PATH = "/static"
TEMPLATES_PATH = os.path.join(BASE_PATH, 'templates')
DOMAIN = 'http://localhost:5000/'

# User management & registration
CONFIRM_REGISTRATIONS_BY_EMAIL = True
ALLOW_REGISTRATION = True
ALLOW_LOGIN = True
ALLOW_CLAIMING = True

USE_SOLR = False
SOLR_URI = 'http://localhost:8983/solr/'

# Sessions
# TODO: Override SECRET_KEY in local.py in production
COOKIE_NAME = 'osf'
SECRET_KEY = 'CHANGEME'

# May set these to True in local.py for development
DEV_MODE = False
DEBUG_MODE = False

# External services
USE_CDN_FOR_CLIENT_LIBS = True

USE_EMAIL = True
FROM_EMAIL = 'openscienceframework-noreply@osf.io'
MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_USERNAME = 'osf-smtp'
MAIL_PASSWORD = ''  # Set this in local.py

# TODO: Override in local.py
MAILGUN_API_KEY = None

# TODO: Override in local.py in production
UPLOADS_PATH = os.path.join(BASE_PATH, 'uploads')
MFR_CACHE_PATH = os.path.join(BASE_PATH, 'mfrcache')

# Use Celery for file rendering
USE_CELERY = True

# File rendering timeout (in ms)
MFR_TIMEOUT = 30000

# TODO: Override in local.py in production
DB_PORT = 20771
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
GRAVATAR_SIZE_PROFILE = 120
GRAVATAR_SIZE_ADD_CONTRIBUTOR = 40
GRAVATAR_SIZE_DISCUSSION = 20

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
    'framework.email.tasks',
    'framework.tasks',
    'framework.render.tasks'
)

# Add-ons

ADDONS_REQUESTED = [
    'wiki', 'osffiles',
    'github', 's3', 'figshare',
    'dropbox',
    # 'badges', 'forward',
    'dataverse',
]

ADDON_CATEGORIES = [
    'documentation', 'storage', 'bibliography', 'other',
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

# Encryption
FINGERPRINT = "F9A58ADF1BEAF2BDDCE337A6154509A46F8DB7B0"
PRIVATE_KEY = """
-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1

lQOYBFOM3jYBCADXkLJzr1YS6jiEkIzJ1QfY09v8DxAPBX+XhGM8beZmoDmCSDSn
s9QIsAzXuaS5yw77hAGZG2hgFL9BybBpyYolzMzK7tCQN2EvNAJSXWMK7sS/tL8w
sE2eT5MuCbybBY/+DffRxRvds9yoR0XI22wywFoimjQvVmydxVmzNHbb+Tm2gZhN
UySaFBDtw7+1aJBy8FHAwFLY/SoWsmsUNeA7J88sSwrk3od8IVYQr6BSHj2HstxC
i7aWKaJYhsG9AYDjHWuUgjIKhaasSYaQEtfarisGfUXGNipLt+SkLttM6FZbyOUT
UZoCnUEocbMtv90ZTYTqO2yFOQP5icDDd9SZABEBAAEAB/9TO17z1QDmh8IvyUJb
EeKYQWEgp047hpN31NmeNQ7vlDDwUWHnWMNnYVZsGxVz2WgdDCCz1cXMx2X7iF0R
04wAQV3XgzNLY96l4657z+wUhhG4tZjWu1QU6sO41HCa6KBq50jHGZTDWxW5cd+L
iNFznRqQXrsEhhmlJ1SVoY29K/0jF0URdmwjbL3UTaYJ97tO3qDQ9ndj9BVAylUW
z4pAC3f0/2r8gN0zdnTwSiLVKYZXOzPrChvxm+h+nO30hkc0axXLOsNkkRSNm96i
2bpbYXYK4p+x3EiCcVz5pQjSsiAoecO1wMhoSuAu61J2GSKBWKG1v3CUjZkuiFwU
KyhzBADX5cdy1NXcY9IgKPweZmHj2zClJMFCrDkrsVJdFUH2qEBnyriIHqHzeLpu
/NWNb76+m596MZ2M7Zz2fw9uxNOB9Al+/l/FLmNC9ps0+On17VLiFx/9FPIjh3cZ
rYVySgGdbGPXNFFX8g1hrgyDm7ZmdvD5FFH4ST54qS2QU+sbCwQA/5sdPRSz4FG5
0RKFvG+HTmT5J+lm6dP52Srjpl5JdEYlTaZC7WfvQjX1fpv1CKNU7xBmSd6RmClo
jFxc4M6gsUaI0PrKcDm2/RK0mpNjNCKQA6rAL0yrdjDFocsQO35d71eWlYREzXu2
A3IA2phrcDSISmV823Nm0lpDltE29WsD/0On3/lFDuAGx/ybvbPW/34LtgMwJ5fR
wl/AFYfiYlqzDDDbMx96ESV1CgD3HIEPevXKcKzOEvq1AgQ7TvLr/Lh0GIUKdpGy
iLT98TwdHjCBT2fHZEv2dhCs/ZCmrX3/J/2Xm8hd3Xg1UCbymRrGH3anYFUw3Mbn
tN5vwOmY0W8KScG0LEF1dG9nZW5lcmF0ZWQgS2V5IDxSTGllYnpAUm9iZXJ0cy1N
YWMubG9jYWw+iQE4BBMBAgAiBQJTjN42AhsvBgsJCAcDAgYVCAIJCgsEFgIDAQIe
AQIXgAAKCRAVRQmkb423sIW8CADQXHPtpujYqphfoyQ3ltYPXNEa20o86YVBUFEP
BKjF6h9tuzFTDrk1Ozjg3/yYSoT9EqsgenEqJAhJ/FzQ6Rm1+hf+9Yy9Q6tGxABt
lFgP+Ik2As3YV8F5ea5qNUnA25xB54RyPRIbENKWC34lWH8aiZAi9EaYl5Dq8/gt
a2hMWSZeMr8SqS0dcKZVV+Zl68N7T93Tt9Ip/auTOGnhVzFRTc0rN0WQWBUEm8Km
3jBkLlCOquDTX38GxCEWpvRAfkKe45UY9NjhGO3ScomofjZl4BpZedKD1swrViQ2
hm8da5nNQyPy1VTd/rnZPJywfUUZrX4u0acRLGY85GaSMZDI
=rz5+
-----END PGP PRIVATE KEY BLOCK-----
"""