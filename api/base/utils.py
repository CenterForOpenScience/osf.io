# -*- coding: utf-8 -*-
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from rest_framework.exceptions import NotFound
from rest_framework.reverse import reverse
import furl

from website import util as website_util  # noqa
from website import settings as website_settings
from framework.auth import Auth, User
from api.base.exceptions import Gone

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


def get_object_or_error(model_cls, query_or_pk, display_name=None, **kwargs):
    if isinstance(query_or_pk, basestring):
        obj = model_cls.load(query_or_pk)
        if obj is None:
            raise NotFound
    else:
        try:
            obj = model_cls.find_one(query_or_pk, **kwargs)
        except NoResultsFound:
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
        (Q('is_collection', 'ne', True) | Q('is_public_files_collection', 'eq', True)) &
        Q('is_registration', 'ne', True)
    )


def default_node_permission_query(user):
    permission_query = Q('is_public', 'eq', True)
    if not user.is_anonymous():
        permission_query = (permission_query | Q('contributors', 'eq', user._id))

    return permission_query

def extend_querystring_params(url, params):
    return furl.furl(url).add(args=params).url
