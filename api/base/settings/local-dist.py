from .defaults import *  # noqa
from website import settings as osf_settings


DEBUG = osf_settings.DEBUG_MODE
VARNISH_SERVERS = ['http://127.0.0.1:8080']
ENABLE_VARNISH = False
ENABLE_ESI = False
CORS_ORIGIN_ALLOW_ALL = True

# Uncomment to get real tracebacks while testing
# DEBUG_PROPAGATE_EXCEPTIONS = True

if DEBUG:
    INSTALLED_APPS += ('debug_toolbar', 'nplusone.ext.django')
    MIDDLEWARE += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        'nplusone.ext.django.NPlusOneMiddleware',
    )
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda _: True,
    }
    ALLOWED_HOSTS.append('localhost')
    ALLOWED_HOSTS.append('192.168.168.167')  # allow requests from GV

    # django-silk
    INSTALLED_APPS += ('silk',)
    MIDDLEWARE += (
        'silk.middleware.SilkyMiddleware',
    )


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'user': '1000000/second',
    'non-cookie-auth': '1000000/second',
    'add-contributor': '1000000/second',
    'create-guid': '1000000/second',
    'root-anon-throttle': '1000000/second',
    'test-user': '2/hour',
    'test-anon': '1/hour',
    'send-email': '2/minute',
    'burst': '10/second',
    'files': '75/minute',
    'files-burst': '3/second',
}

# Can switch between using Redis and using postgres as session storage
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
