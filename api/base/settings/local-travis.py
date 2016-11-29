VARNISH_SERVERS = ['http://127.0.0.1:8080']
ENABLE_VARNISH = True
ENABLE_ESI = False

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    # Order is important here because of a bug in rest_framework_swagger. For now,
    # rest_framework.renderers.JSONRenderer needs to be first, at least until
    # https://github.com/marcgibbons/django-rest-swagger/issues/271 is resolved.
    'DEFAULT_RENDERER_CLASSES': (
        'api.base.renderers.JSONAPIRenderer',
        'api.base.renderers.JSONRendererWithESISupport',
        'api.base.renderers.BrowsableAPIRendererNoForms',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'api.base.parsers.JSONAPIParser',
        'api.base.parsers.JSONAPIParserForRegularJSON',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ),
    'EXCEPTION_HANDLER': 'api.base.exceptions.json_api_exception_handler',
    'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'api.base.content_negotiation.JSONAPIContentNegotiation',
    'DEFAULT_VERSIONING_CLASS': 'api.base.versioning.BaseVersioning',
    'DEFAULT_VERSION': '2.0',
    # The versions below are specifically for testing purposes and do not reflect the actual versioning of the API.
    # If changes are made to this list, or to DEFAULT_VERSION above, please reflect those changes in
    # api_tests/base/test_versioning.py so that local tests will pass.
    'ALLOWED_VERSIONS': (
        '2.0',
        '2.0.1',
        '2.1',
        '2.2',
        '3.0',
        '3.0.1',
    ),
    'DEFAULT_FILTER_BACKENDS': ('api.base.filters.ODMOrderingFilter',),
    'DEFAULT_PAGINATION_CLASS': 'api.base.pagination.JSONAPIPagination',
    'ORDERING_PARAM': 'sort',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Custom auth classes
        'api.base.authentication.drf.OSFBasicAuthentication',
        'api.base.authentication.drf.OSFSessionAuthentication',
        'api.base.authentication.drf.OSFCASAuthentication'
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
        'api.base.throttling.NonCookieAuthThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000000/hour',
        'non-cookie-auth': '1000000/hour',
        'add-contributor': '10/second',
        'create-guid': '1000/hour',
        'root-anon-throttle': '1000/hour',
        'test-user': '2/hour',
        'test-anon': '1/hour',
    }
}
