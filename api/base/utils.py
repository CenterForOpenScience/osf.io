# -*- coding: utf-8 -*-
import furl
from django.core.exceptions import ObjectDoesNotExist
from modularodm import Q
from rest_framework.exceptions import NotFound
from rest_framework.reverse import reverse

from api.base.authentication.drf import get_session_from_cookie
from api.base.exceptions import Gone
from framework.auth import Auth, User
from framework.auth.cas import CasResponse
from framework.auth.oauth_scopes import ComposedScopes, normalize_scopes
from osf.models.base import GuidMixin
from osf.modm_compat import to_django_query
from website import settings as website_settings
from website import util as website_util  # noqa

# These values are copied from rest_framework.fields.BooleanField
# BooleanField cannot be imported here without raising an
# ImproperlyConfigured error
TRUTHY = set(('t', 'T', 'true', 'True', 'TRUE', '1', 1, True))
FALSY = set(('f', 'F', 'false', 'False', 'FALSE', '0', 0, 0.0, False))

UPDATE_METHODS = ['PUT', 'PATCH']

def decompose_field(field):
    from api.base.serializers import (
        HideIfWithdrawal, HideIfRegistration,
        HideIfDisabled, AllowMissing
    )
    WRAPPER_FIELDS = (HideIfWithdrawal, HideIfRegistration, HideIfDisabled, AllowMissing)

    while isinstance(field, WRAPPER_FIELDS):
        try:
            field = getattr(field, 'field')
        except AttributeError:
            break
    return field

def is_bulk_request(request):
    """
    Returns True if bulk request.  Can be called as early as the parser.
    """
    content_type = request.content_type
    return 'ext=bulk' in content_type

def is_truthy(value):
    return value in TRUTHY

def is_falsy(value):
    return value in FALSY

def get_user_auth(request):
    """Given a Django request object, return an ``Auth`` object with the
    authenticated user attached to it.
    """
    user = request.user
    private_key = request.query_params.get('view_only', None)
    if user.is_anonymous():
        auth = Auth(None, private_key=private_key)
    else:
        auth = Auth(user, private_key=private_key)
    return auth


def absolute_reverse(view_name, query_kwargs=None, args=None, kwargs=None):
    """Like django's `reverse`, except returns an absolute URL. Also add query parameters."""
    relative_url = reverse(view_name, kwargs=kwargs)

    url = website_util.api_v2_url(relative_url, params=query_kwargs, base_prefix='')
    return url


def get_object_or_error(model_cls, query_or_pk, display_name=None, prefetch_fields=()):
    obj = query = None
    if isinstance(query_or_pk, basestring):
        # they passed a 5-char guid as a string
        if issubclass(model_cls, GuidMixin):
            # if it's a subclass of GuidMixin we know it's primary_identifier_name
            query = {'guids___id': query_or_pk}
        else:
            if hasattr(model_cls, 'primary_identifier_name'):
                # primary_identifier_name gives us the natural key for the model
                query = {model_cls.primary_identifier_name: query_or_pk}
            else:
                # fall back to modmcompatiblity's load method since we don't know their PIN
                obj = model_cls.load(query_or_pk)
    else:
        # they passed a query
        if hasattr(model_cls, 'primary_identifier_name'):
            query = to_django_query(query_or_pk, model_cls=model_cls)
        else:
            # fall back to modmcompatibility's find_one
            obj = model_cls.find_one(query_or_pk)

    if not obj:
        if not query:
            # if we don't have a query or an object throw 404
            raise NotFound
        try:
            # eagerly prefetch/select_related fields that are on the serializer
            if isinstance(query, dict):
                obj = model_cls.objects.eager(*prefetch_fields).get(**query)
            else:
                obj = model_cls.objects.eager(*prefetch_fields).get(query)
        except ObjectDoesNotExist:
            raise NotFound

    # For objects that have been disabled (is_active is False), return a 410.
    # The User model is an exception because we still want to allow
    # users who are unconfirmed or unregistered, but not users who have been
    # disabled.
    if model_cls is User and obj.is_disabled:
        raise Gone(detail='The requested user is no longer available.',
                   meta={'full_name': obj.fullname, 'family_name': obj.family_name, 'given_name': obj.given_name,
                         'middle_names': obj.middle_names, 'profile_image': obj.profile_image_url()})
    elif model_cls is not User and not getattr(obj, 'is_active', True) or getattr(obj, 'is_deleted', False):
        if display_name is None:
            raise Gone
        else:
            raise Gone(detail='The requested {name} is no longer available.'.format(name=display_name))
    return obj


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

def default_node_list_query():
    return (
        Q('is_deleted', 'ne', True) &
        Q('type', 'eq', 'osf.node')
    )


def default_node_permission_query(user):
    permission_query = Q('is_public', 'eq', True)
    if not user.is_anonymous():
        permission_query = (permission_query | Q('contributors', 'eq', user.pk))

    return permission_query

def extend_querystring_params(url, params):
    return furl.furl(url).add(args=params).url

def extend_querystring_if_key_exists(url, request, key):
    if key in request.query_params.keys():
        return extend_querystring_params(url, {key: request.query_params.get(key)})
    return url

def has_admin_scope(request):
    """ Helper function to determine if a request should be treated
        as though it has the `osf.admin` scope. This includes both
        tokened requests that do, and requests that are made via the
        OSF (i.e. have an osf cookie)
    """
    cookie = request.COOKIES.get(website_settings.COOKIE_NAME)
    if cookie:
        return bool(get_session_from_cookie(cookie))

    token = request.auth
    if token is None or not isinstance(token, CasResponse):
        return False

    return set(ComposedScopes.ADMIN_LEVEL).issubset(normalize_scopes(token.attributes['accessTokenScope']))

def is_deprecated(request_version, min_version, max_version):
    if request_version < min_version or request_version > max_version:
        return True
    return False
