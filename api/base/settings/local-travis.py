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
    'send-email': '2/minute',
}

ALLOWED_HOSTS.append('localhost')
# TODO: Remove this when we're using Elasticsearch 6 for everything
ENABLE_ELASTICSEARCH_METRICS = False
