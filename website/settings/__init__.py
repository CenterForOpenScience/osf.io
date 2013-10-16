# -*- coding: utf-8 -*-
'''Consolidates settings from base.py and local.py.

::
    >>> from website import settings
    >>> settings.mail_server
    'smtp.sendgrid.net'
'''
from .base import *

try:
    from .local import *
except ImportError as error:
    raise ImportError("No local.py settings file found. Did you remember to "
                        "copy local-dist.py to local.py?")
