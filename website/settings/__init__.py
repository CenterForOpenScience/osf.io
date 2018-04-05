# -*- coding: utf-8 -*-
'''Consolidates settings from defaults.py and local.py.

::
    >>> from website import settings
    >>> settings.MAIL_SERVER
    'smtp.sendgrid.net'
'''
import os
from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError as error:
    raise ImportError("No local.py settings file found. Did you remember to "
                        "copy local-dist.py to local.py?")

# apply environment variables
globals().update(os.environ)

if not DEV_MODE:
    from . import local
    from . import defaults
    for setting in ('WATERBUTLER_JWE_SECRET', 'WATERBUTLER_JWE_SALT', 'WATERBUTLER_JWT_SECRET', 'JWT_SECRET', 'DEFAULT_HMAC_SECRET', 'POPULAR_LINKS_NODE', 'NEW_AND_NOTEWORTHY_LINKS_NODE', 'SENSITIVE_DATA_SALT', 'SENSITIVE_DATA_SECRET'):
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), '{} must be specified in local.py when DEV_MODE is False'.format(setting)


def bool_from_str(s):
    return s.lower() in ['true', 'yes', 'on', '1']

import sys
this = sys.modules[__name__]

def to_bool(name, default):
    if hasattr(this, name):
        val = getattr(this, name)
        if isinstance(val, bool):
            return val
        else:
            return bool_from_str(val)
    return default
