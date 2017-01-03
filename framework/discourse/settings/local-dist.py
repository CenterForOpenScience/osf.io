# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''

from . import defaults

DISCOURSE_SSO_SECRET = 'changeme'
DISCOURSE_DEV_MODE = True
DISCOURSE_SERVER_URL = 'http://localhost:4000/' if DISCOURSE_DEV_MODE else 'http://192.168.99.100'
DISCOURSE_API_KEY = 'changeme' if DISCOURSE_DEV_MODE else 'changeme'
DISCOURSE_API_ADMIN_USER = 'system'

DISCOURSE_CONTACT_EMAIL = 'changeme'

DISCOURSE_LOG_REQUESTS = True

DISCOURSE_SERVER_SETTINGS = defaults.DISCOURSE_SERVER_SETTINGS
DISCOURSE_SERVER_SETTINGS.update({
    'contact_email': DISCOURSE_CONTACT_EMAIL,
    'sso_secret': DISCOURSE_SSO_SECRET,
})

if DISCOURSE_DEV_MODE:
    DISCOURSE_SERVER_SETTINGS.update({'port': '4000'})
