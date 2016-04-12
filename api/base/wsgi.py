"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""
from website import settings
from api.base import settings as api_settings

if not settings.DEBUG_MODE:
    from gevent import monkey
    monkey.patch_all()
    # PATCH: avoid deadlock on getaddrinfo, this patch is necessary while waiting for
    # the final gevent 1.1 release (https://github.com/gevent/gevent/issues/349)
    unicode('foo').encode('idna')  # noqa


import os  # noqa
from django.core.wsgi import get_wsgi_application  # noqa
from website.app import init_app  # noqa

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.base.settings')

import six
import sys
from rest_framework.request import Request

Request.__getattribute__ = object.__getattribute__

def __getattr__(self, attr):
    try:
        return getattr(self._request, attr)
    except AttributeError:
        info = sys.exc_info()
        six.reraise(info[0], info[1], info[2].tb_next)

Request.__getattr__ = __getattr__

init_app(set_backends=True, routes=False, attach_request_handlers=False)

application = get_wsgi_application()
