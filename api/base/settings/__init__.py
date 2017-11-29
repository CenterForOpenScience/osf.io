# -*- coding: utf-8 -*-
'''Consolidates settings from defaults.py and local.py.

::
    >>> from api.base import settings
    >>> settings.API_BASE
    'v2/'
'''
import os
from urlparse import urlparse
import warnings
import itertools

from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError as error:
    warnings.warn('No api/base/settings/local.py settings file found. Did you remember to '
                  'copy local-dist.py to local.py?', ImportWarning)

if not DEV_MODE and os.environ.get('DJANGO_SETTINGS_MODULE') == 'api.base.settings':
    from . import local
    from . import defaults
    for setting in ('JWE_SECRET', 'JWT_SECRET', 'BYPASS_THROTTLE_TOKEN'):
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), '{} must be specified in local.py when DEV_MODE is False'.format(setting)

def load_origins_whitelist():
    global ORIGINS_WHITELIST
    from osf.models import Institution, PreprintProvider

    institution_origins = tuple(domain.lower() for domain in itertools.chain(*Institution.objects.values_list('domains', flat=True)))

    preprintprovider_origins = tuple(preprintprovider.domain.lower() for preprintprovider in PreprintProvider.objects.exclude(domain=''))

    ORIGINS_WHITELIST = tuple(urlparse(url).geturl().lower().split('{}://'.format(urlparse(url).scheme))[-1] for url in institution_origins + preprintprovider_origins)
