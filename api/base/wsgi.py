"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""
from website import settings

if settings.NEWRELIC_INI_PATH:
    try:
        import newrelic.agent
        newrelic.agent.initialize(settings.NEWRELIC_INI_PATH)
    except Exception as err:
        raise Exception(f'Unable to initialize newrelic! {err}')

from api.base import settings as api_settings

import os  # noqa
from django.core.wsgi import get_wsgi_application  # noqa
from django.conf import settings as django_settings
from website.app import init_app  # noqa

if os.environ.get('API_REMOTE_DEBUG', None):
    import pydevd
    remote_parts = os.environ.get('API_REMOTE_DEBUG').split(':')
    pydevd.settrace(remote_parts[0], port=int(remote_parts[1]), suspend=False, stdoutToServer=True, stderrToServer=True, trace_only_current_thread=False)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.base.settings')

#### WARNING: Here be monkeys ###############
import sys
from rest_framework.fields import Field
from rest_framework.request import Request

# Cached properties break internal caching
# 792005806b50f8aad086a76ff5a742c66a98428e
@property
def context(self):
    return getattr(self.root, '_context', {})


# Overriding __getattribute__ is super slow
def __getattr__(self, attr):
    try:
        return getattr(self._request, attr)
    except AttributeError:
        info = sys.exc_info()
        raise info[1].with_traceback(info[2].tb_next)

Field.context = context
Request.__getattr__ = __getattr__
Request.__getattribute__ = object.__getattribute__
############# /monkeys ####################

init_app(set_backends=True, routes=False, attach_request_handlers=False)
api_settings.load_origins_whitelist()
django_settings.CORS_ORIGIN_WHITELIST = list(set(django_settings.CORS_ORIGIN_WHITELIST) | set(api_settings.ORIGINS_WHITELIST))

application = get_wsgi_application()
