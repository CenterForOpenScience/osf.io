# -*- coding: utf-8 -*-
'''Consolidates settings from defaults.py and local.py.

::
    >>> from api.base import settings
    >>> settings.API_BASE
    'v2/'
'''
from .defaults import *

try:
    from .local import *
except ImportError as error:
    raise ImportError("No api/base/settings/local.py settings file found. Did you remember to "
                        "copy local-dist.py to local.py?")
