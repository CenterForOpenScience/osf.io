from .defaults import *  # noqa


VARNISH_SERVERS = ['http://127.0.0.1:8080']
ENABLE_VARNISH = True
ENABLE_ESI = False


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'user': '1000000/second',
    'non-cookie-auth': '1000000/second',
    'add-contributor': '1000000/second',
    'create-guid': '1000000/second',
    'root-anon-throttle': '1000000/second',
    'test-user': '2/hour',
    'test-anon': '1/hour',
}

ALLOWED_HOSTS.append('localhost')
KEY_SAVE_PATH = './user_key_info/'
