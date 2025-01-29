import os
import warnings

from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError:
    warnings.warn(
        'No addons/onlyoffice/settings/local.py settings file found. Did you remember to '
        'copy local-dist.py to local.py?', ImportWarning,
    )

if not DEV_MODE and os.environ.get('DJANGO_SETTINGS_MODULE') == 'addons.onlyoffice.settings':
    from . import local
    from . import defaults
    for setting in ('OFFICESERVER_JWE_SECRET', 'OFFICESERVER_JWE_SALT', 'OFFICESERVER_JWT_SECRET'):
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), '{} must be specified in local.py when DEV_MODE is False'.format(setting)
