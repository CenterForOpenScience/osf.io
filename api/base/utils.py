# -*- coding: utf-8 -*-

import furl

from modularodm import Q
from rest_framework.reverse import reverse
from rest_framework.exceptions import NotFound
from modularodm.exceptions import NoResultsFound

from website import util as website_util  # noqa
from website import settings as website_settings

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from rest_framework import status, exceptions
from rest_framework.response import Response



def absolute_reverse(view_name, query_kwargs=None, args=None, kwargs=None):
    """Like django's `reverse`, except returns an absolute URL. Also add query parameters."""
    relative_url = reverse(view_name, kwargs=kwargs)

    url = website_util.api_v2_url(relative_url, params=query_kwargs)
    return url


def get_object_or_404(model_cls, query_or_pk):
    if isinstance(query_or_pk, basestring):
        query = Q('_id', 'eq', query_or_pk)
    else:
        query = query_or_pk
    try:
        return model_cls.find_one(query)
    except NoResultsFound:
        raise NotFound


def waterbutler_url_for(request_type, provider, path, node_id, token, obj_args=None, **query):
    """Reverse URL lookup for WaterButler routes
    :param str request_type: data or metadata
    :param str provider: The name of the requested provider
    :param str path: The path of the requested file or folder
    :param str node_id: The id of the node being accessed
    :param str token: The cookie to be used or None
    :param dict **query: Addition query parameters to be appended
    """
    url = furl.furl(website_settings.WATERBUTLER_URL)
    url.path.segments.append(request_type)

    url.args.update({
        'path': path,
        'nid': node_id,
        'provider': provider,
    })

    if token is not None:
        url.args['cookie'] = token

    if 'view_only' in obj_args:
        url.args['view_only'] = obj_args['view_only']

    url.args.update(query)
    return url.url

def custom_exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `ValidationError`, `Http404` and `PermissionDenied`
    exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        return Response(data, status=exc.status_code, headers=headers)

    elif isinstance(exc, Http404):
        msg = _('Not found.')
        data = {'detail': six.text_type(msg)}
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    elif isinstance(exc, PermissionDenied):
        msg = _('Permission denied.')
        data = {'detail': six.text_type(msg)}
        return Response(data, status=status.HTTP_403_FORBIDDEN)

    # Note: Unhandled exceptions will raise a 500 error.
    return None