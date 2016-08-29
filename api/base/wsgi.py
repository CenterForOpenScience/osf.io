
from __future__ import unicode_literals
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

#### WARNING: Here be monkeys ###############
import six
import sys
import re
from django.contrib.admindocs import views
from rest_framework.fields import Field
from rest_framework.request import Request
import urlparse
from coreapi.compat import force_bytes
from openapi_codec import OpenAPICodec, encode
import simplejson as json

def generate_swagger_object(document):
    """
    Generates root of the Swagger spec.
    """
    parsed_url = urlparse.urlparse(document.url)

    return {
        'swagger': '2.0',
        'info': encode._get_info_object(document),
        'tags': _get_tags_object(document),
        'paths': encode._get_paths_object(document),
        'host': parsed_url.netloc,
    }

def _get_tags_object(document):
    return [{'name': tag, 'description': 'No Description'} for tag in sorted({tag for tag, _object in document.data.items()})]

def dump(self, document, **kwargs):
    data = generate_swagger_object(document)
    return force_bytes(json.dumps(data))

OpenAPICodec.dump = dump

named_group_matcher = re.compile(r'\(\?P(<\w+>)[^\)]+\)')
non_named_group_matcher = re.compile(r'\(.*?\)')

def simplify_regex(pattern):
    """
    Clean up urlpattern regexes into something somewhat readable by Mere Humans:
    turns something like "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
    into "<sport_slug>/athletes/<athlete_slug>/"
    """
    # handle named groups first
    pattern = named_group_matcher.sub(lambda m: m.group(1), pattern)

    # handle non-named groups
    pattern = non_named_group_matcher.sub('<var>', pattern)

    # clean up any outstanding regex-y characters.
    pattern = pattern.replace('^', '').replace('$', '').replace('?', '').replace('//', '/').replace('\\', '')
    if not pattern.startswith('/'):
        pattern = '/' + pattern
    return pattern

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
        six.reraise(info[0], info[1], info[2].tb_next)

views.simplify_regex = simplify_regex
Field.context = context
Request.__getattr__ = __getattr__
Request.__getattribute__ = object.__getattribute__

############# /monkeys ####################

init_app(set_backends=True, routes=False, attach_request_handlers=False)
api_settings.load_institutions()

application = get_wsgi_application()
