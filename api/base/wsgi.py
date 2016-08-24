
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
from django.core.handlers.base import BaseHandler
from rest_framework.fields import Field
from rest_framework.request import Request

# for get_response

import logging
import sys
import types
import warnings

from django import http
from django.conf import settings
from django.core import signals, urlresolvers
from django.core.exceptions import (
    MiddlewareNotUsed, PermissionDenied, SuspiciousOperation,
)
from django.db import connections, transaction
from django.http.multipartparser import MultiPartParserError
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.views import debug

logger = logging.getLogger('django.request')


def get_response(self, request):
    "Returns an HttpResponse object for the given HttpRequest"

    from pprint import pprint

    # Setup default url resolver for this thread, this code is outside
    # the try/except so we don't get a spurious "unbound local
    # variable" exception in the event an exception is raised before
    # resolver is set
    urlconf = settings.ROOT_URLCONF
    urlresolvers.set_urlconf(urlconf)
    resolver = urlresolvers.get_resolver(urlconf)
    # Use a flag to check if the response was rendered to prevent
    # multiple renderings or to force rendering if necessary.
    response_is_rendered = False
    try:
        response = None
        # Apply request middleware
        for middleware_method in self._request_middleware:

            pprint(response)

            response = middleware_method(request)
            if response:
                break

        if response is None:
            if hasattr(request, 'urlconf'):
                # Reset url resolver with a custom URLconf.
                urlconf = request.urlconf
                urlresolvers.set_urlconf(urlconf)
                resolver = urlresolvers.get_resolver(urlconf)

            resolver_match = resolver.resolve(request.path_info)
            callback, callback_args, callback_kwargs = resolver_match
            request.resolver_match = resolver_match

            # Apply view middleware
            for middleware_method in self._view_middleware:
                response = middleware_method(request, callback, callback_args, callback_kwargs)
                if response:
                    break

        if response is None:
            wrapped_callback = self.make_view_atomic(callback)
            try:
                response = wrapped_callback(request, *callback_args, **callback_kwargs)
            except Exception as e:
                response = self.process_exception_by_middleware(e, request)

        # Complain if the view returned None (a common error).
        if response is None:
            if isinstance(callback, types.FunctionType):    # FBV
                view_name = callback.__name__
            else:                                           # CBV
                view_name = callback.__class__.__name__ + '.__call__'
            raise ValueError("The view %s.%s didn't return an HttpResponse object. It returned None instead."
                             % (callback.__module__, view_name))

        # If the response supports deferred rendering, apply template
        # response middleware and then render the response
        if hasattr(response, 'render') and callable(response.render):
            for middleware_method in self._template_response_middleware:
                response = middleware_method(request, response)
                # Complain if the template response middleware returned None (a common error).
                if response is None:
                    raise ValueError(
                        "%s.process_template_response didn't return an "
                        "HttpResponse object. It returned None instead."
                        % (middleware_method.__self__.__class__.__name__))
            try:
                response = response.render()
            except Exception as e:
                response = self.process_exception_by_middleware(e, request)

            response_is_rendered = True

    except http.Http404 as exc:
        logger.warning('Not Found: %s', request.path,
                    extra={
                        'status_code': 404,
                        'request': request
                    })
        if settings.DEBUG:
            response = debug.technical_404_response(request, exc)
        else:
            response = self.get_exception_response(request, resolver, 404, exc)

    except PermissionDenied as exc:
        logger.warning(
            'Forbidden (Permission denied): %s', request.path,
            extra={
                'status_code': 403,
                'request': request
            })
        response = self.get_exception_response(request, resolver, 403, exc)

    except MultiPartParserError as exc:
        logger.warning(
            'Bad request (Unable to parse request body): %s', request.path,
            extra={
                'status_code': 400,
                'request': request
            })
        response = self.get_exception_response(request, resolver, 400, exc)

    except SuspiciousOperation as exc:
        # The request logger receives events for any problematic request
        # The security logger receives events for all SuspiciousOperations
        security_logger = logging.getLogger('django.security.%s' % exc.__class__.__name__)
        security_logger.error(
            force_text(exc),
            extra={
                'status_code': 400,
                'request': request
            })
        if settings.DEBUG:
            return debug.technical_500_response(request, *sys.exc_info(), status_code=400)

        response = self.get_exception_response(request, resolver, 400, exc)

    except SystemExit:
        # Allow sys.exit() to actually exit. See tickets #1023 and #4701
        raise

    except:  # Handle everything else.
        # Get the exception info now, in case another exception is thrown later.
        signals.got_request_exception.send(sender=self.__class__, request=request)
        response = self.handle_uncaught_exception(request, resolver, sys.exc_info())

    try:
        # Apply response middleware, regardless of the response
        for middleware_method in self._response_middleware:
            response = middleware_method(request, response)
            # Complain if the response middleware returned None (a common error).
            if response is None:
                raise ValueError(
                    "%s.process_response didn't return an "
                    "HttpResponse object. It returned None instead."
                    % (middleware_method.__self__.__class__.__name__))
            response = self.apply_response_fixes(request, response)
    except:  # Any exception should be gathered and handled
        signals.got_request_exception.send(sender=self.__class__, request=request)
        response = self.handle_uncaught_exception(request, resolver, sys.exc_info())

    response._closable_objects.append(request)

    # If the exception handler returns a TemplateResponse that has not
    # been rendered, force it to be rendered.
    if not response_is_rendered and callable(getattr(response, 'render', None)):
        response = response.render()

    return response

BaseHandler.get_response = get_response

named_group_matcher = re.compile(r'\(\?P(<\w+>).+?[^/]\)')
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
