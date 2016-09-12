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
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': '2.0',
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
        'root-anon-throttle': '1000/hour',
        'test-user': '2/hour',
        'test-anon': '1/hour',
    }
}
