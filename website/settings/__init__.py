'''Consolidates settings from defaults.py and local.py.

::
    >>> from website import settings
    >>> settings.MAIL_SERVER
    'smtp.sendgrid.net'
'''
from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError:
    raise ImportError('No local.py settings file found. Did you remember to '
                        'copy local-dist.py to local.py?')

# apply environment variables
globals().update(os.environ)

# Environment variables arrive as strings, so a date configured that way shows up as e.g. 2026-09-29
if isinstance(LATEST_TERMS_OF_SERVICE_UPDATE, str):
    LATEST_TERMS_OF_SERVICE_UPDATE = datetime.datetime.fromisoformat(LATEST_TERMS_OF_SERVICE_UPDATE)

if LATEST_TERMS_OF_SERVICE_UPDATE and LATEST_TERMS_OF_SERVICE_UPDATE.tzinfo is None:
    LATEST_TERMS_OF_SERVICE_UPDATE = LATEST_TERMS_OF_SERVICE_UPDATE.replace(tzinfo=datetime.timezone.utc)

if not DEV_MODE:
    from . import local
    from . import defaults
    for setting in ('WATERBUTLER_JWE_SECRET', 'WATERBUTLER_JWE_SALT', 'WATERBUTLER_JWT_SECRET', 'JWT_SECRET', 'DEFAULT_HMAC_SECRET', 'POPULAR_LINKS_NODE', 'NEW_AND_NOTEWORTHY_LINKS_NODE', 'SENSITIVE_DATA_SALT', 'SENSITIVE_DATA_SECRET'):
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), f'{setting} must be specified in local.py when DEV_MODE is False'
