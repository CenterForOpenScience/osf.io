# -*- coding: utf-8 -*-
'''Consolidates settings from defaults.py and local.py.

::
    >>> from framework.discourse import settings
    >>> settings.DISCOURSE_SERVER_URL
    'http://localhost:4000/'
'''
import os

from .defaults import *  # noqa
from website.settings import DEV_MODE

try:
    from .local import *  # noqa
except ImportError as error:
    warnings.warn('No api/base/settings/local.py settings file found. Did you remember to '
                  'copy local-dist.py to local.py?', ImportWarning)

# apply environment variables
globals().update(os.environ)

if not DEV_MODE:
    from . import local
    from . import defaults
    for setting in ('DISCOURSE_API_KEY', 'DISCOURSE_SSO_SECRET', 'DISCOURSE_CONTACT_EMAIL'):
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), '{} must be specified in local.py when DEV_MODE is False'.format(setting)
