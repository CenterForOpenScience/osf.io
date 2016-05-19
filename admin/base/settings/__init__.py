# -*- coding: utf-8 -*-
"""Consolidates settings from defaults.py and local.py.

::
    >>> from admin.base import settings
    >>> settings.ADMIN_BASE
    'admin/'
"""
import warnings

from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError as error:
    warnings.warn('No admin/base/settings/local.py settings file found. Did you remember to '
                  'copy local-dist.py to local.py?', ImportWarning)
