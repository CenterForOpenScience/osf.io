from .defaults import *  # noqa
from website import settings as osf_settings


DEBUG = osf_settings.DEBUG_MODE
VARNISH_SERVERS = ['http://127.0.0.1:8080']
ENABLE_VARNISH = False
ENABLE_ESI = False
CORS_ORIGIN_ALLOW_ALL = True

if DEBUG:
    ALLOWED_HOSTS.append('localhost')

    MIDDLEWARE += (
        'django.contrib.sessions.middleware.SessionMiddleware',
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
}
