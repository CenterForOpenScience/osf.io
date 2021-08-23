# -*- coding: utf-8 -*-
from past.builtins import basestring
import furl
from future.moves.urllib.parse import urlunsplit, urlsplit, parse_qs, urlencode
from distutils.version import StrictVersion
from hashids import Hashids

from django.utils.http import urlquote
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet, F
from rest_framework.exceptions import NotFound
from rest_framework.reverse import reverse

from api.base.authentication.drf import get_session_from_cookie
from api.base.exceptions import Gone, UserGone
from api.base.settings import HASHIDS_SALT
from framework.auth import Auth
from framework.auth.cas import CasResponse
from framework.auth.oauth_scopes import ComposedScopes, normalize_scopes
from osf.models import OSFUser, Node, Registration
from osf.models.base import GuidMixin
from osf.utils.requests import check_select_for_update
from website import settings as website_settings
from website import util as website_util  # noqa

# These values are copied from rest_framework.fields.BooleanField
# BooleanField cannot be imported here without raising an
# ImproperlyConfigured error
TRUTHY = set(('t', 'T', 'true', 'True', 'TRUE', '1', 1, True, 'on', 'ON', 'On', 'y', 'Y', 'YES', 'yes'))
FALSY = set(('f', 'F', 'false', 'False', 'FALSE', '0', 0, 0.0, False, 'off', 'OFF', 'Off', 'n', 'N', 'NO', 'no'))

UPDATE_METHODS = ['PUT', 'PATCH']

hashids = Hashids(alphabet='abcdefghijklmnopqrstuvwxyz', salt=HASHIDS_SALT)

def decompose_field(field):
    from api.base.serializers import (
        HideIfWithdrawal, HideIfRegistration,
        HideIfDisabled, AllowMissing, NoneIfWithdrawal,
    )
    WRAPPER_FIELDS = (HideIfWithdrawal, HideIfRegistration, HideIfDisabled, AllowMissing, NoneIfWithdrawal)

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
    if user.is_anonymous:
        auth = Auth(None, private_key=private_key)
    else:
        auth = Auth(user, private_key=private_key)
    return auth


def absolute_reverse(view_name, query_kwargs=None, args=None, kwargs=None):
    """Like django's `reverse`, except returns an absolute URL. Also add query parameters."""
    relative_url = reverse(view_name, kwargs=kwargs)

    url = website_util.api_v2_url(relative_url, params=query_kwargs, base_prefix='')
    return url


def get_object_or_error(model_or_qs, query_or_pk=None, request=None, display_name=None, check_deleted=True):
    if not request:
        # for backwards compat with existing get_object_or_error usages
        raise TypeError('request is a required argument')

    obj = query = None
    model_cls = model_or_qs
    select_for_update = check_select_for_update(request)

    if isinstance(model_or_qs, QuerySet):
        # they passed a queryset
        model_cls = model_or_qs.model
        try:
            obj = model_or_qs.select_for_update().get() if select_for_update else model_or_qs.get()
        except model_cls.DoesNotExist:
            raise NotFound

    elif isinstance(query_or_pk, basestring):
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
                obj = model_cls.load(query_or_pk, select_for_update=select_for_update)
    else:
        # they passed a query
        try:
            obj = model_cls.objects.filter(query_or_pk).select_for_update().get() if select_for_update else model_cls.objects.get(query_or_pk)
        except model_cls.DoesNotExist:
            raise NotFound

    if not obj:
        if not query:
            # if we don't have a query or an object throw 404
            raise NotFound
        try:
            # TODO This could be added onto with eager on the queryset and the embedded fields of the api
            if isinstance(query, dict):
                obj = model_cls.objects.get(**query) if not select_for_update else model_cls.objects.filter(**query).select_for_update().get()
            else:
                obj = model_cls.objects.get(query) if not select_for_update else model_cls.objects.filter(query).select_for_update().get()
        except ObjectDoesNotExist:
            raise NotFound

    # For objects that have been disabled (is_active is False), return a 410.
    # The User model is an exception because we still want to allow
    # users who are unconfirmed or unregistered, but not users who have been
    # disabled.
    if model_cls is OSFUser and obj.is_disabled:
        raise UserGone(user=obj)
    if check_deleted and (model_cls is not OSFUser and not getattr(obj, 'is_active', True) or getattr(obj, 'is_deleted', False) or getattr(obj, 'deleted', False)):
        if display_name is None:
            raise Gone
        else:
            raise Gone(detail='The requested {name} is no longer available.'.format(name=display_name))
    return obj

def default_node_list_queryset(model_cls):
    assert model_cls in {Node, Registration}
    return model_cls.objects.filter(is_deleted=False).annotate(region=F('addons_osfstorage_node_settings__region___id'))

def default_node_permission_queryset(user, model_cls):
    """
    Return nodes that are either public or you have perms because you're a contributor.
    Implicit admin permissions not included here (NodeList, UserNodes, for example, don't factor this in.)
    """
    assert model_cls in {Node, Registration}
    return model_cls.objects.get_nodes_for_user(user, include_public=True)

def default_node_list_permission_queryset(user, model_cls):
    # **DO NOT** change the order of the querysets below.
    # If get_roots() is called on default_node_list_qs & default_node_permission_qs,
    # Django's alaising will break and the resulting QS will be empty and you will be sad.
    qs = default_node_permission_queryset(user, model_cls) & default_node_list_queryset(model_cls)
    return qs.annotate(region=F('addons_osfstorage_node_settings__region___id'))

def extend_querystring_params(url, params):
    scheme, netloc, path, query, _ = urlsplit(url)
    orig_params = parse_qs(query)
    orig_params.update(params)
    query = urlencode(orig_params, True)
    return urlunsplit([scheme, netloc, path, query, ''])

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


def has_pigeon_scope(request):
    """ Helper function to determine if a request token has OSF pigeon scope
    """
    token = request.auth
    if token is None or not isinstance(token, CasResponse):
        return False

    if token.attributes['accessToken'] == website_settings.PIGEON_CALLBACK_BEARER_TOKEN:
        return True
    else:
        return False


def is_deprecated(request_version, min_version=None, max_version=None):
    if not min_version and not max_version:
        raise NotImplementedError('Must specify min or max version.')
    min_version_deprecated = min_version and StrictVersion(request_version) < StrictVersion(str(min_version))
    max_version_deprecated = max_version and StrictVersion(request_version) > StrictVersion(str(max_version))
    if min_version_deprecated or max_version_deprecated:
        return True
    return False


def waterbutler_api_url_for(node_id, provider, path='/', _internal=False, base_url=None, **kwargs):
    assert path.startswith('/'), 'Path must always start with /'
    if provider != 'osfstorage':
        base_url = None
    url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL if _internal else (base_url or website_settings.WATERBUTLER_URL))
    segments = ['v1', 'resources', node_id, 'providers', provider] + path.split('/')[1:]
    url.path.segments.extend([urlquote(x) for x in segments])
    url.args.update(kwargs)
    return url.url

def assert_resource_type(obj, resource_tuple):
    assert type(resource_tuple) is tuple, 'resources must be passed in as a tuple.'
    if len(resource_tuple) == 1:
        error_message = resource_tuple[0].__name__
    elif len(resource_tuple) == 2:
        error_message = resource_tuple[0].__name__ + ' or ' + resource_tuple[1].__name__
    else:
        error_message = ''
        for resource in resource_tuple[:-1]:
            error_message += resource.__name__ + ', '
        error_message += 'or ' + resource_tuple[-1].__name__

    a_or_an = 'an' if error_message[0].lower() in 'aeiou' else 'a'
    assert isinstance(obj, resource_tuple), 'obj must be {} {}; got {}'.format(a_or_an, error_message, obj)


class MockQueryset(list):
    """
    This class is meant to convert a simple list into a filterable queryset look-a-like.
    """

    def __init__(self, items, search, default_attrs=None, **kwargs):
        self.search = search

        for item in items:
            if default_attrs:
                item.update(default_attrs)
            self.add_dict_as_item(item)

    def __len__(self):
        return self.search.count()

    def add_dict_as_item(self, dict):
        item = type('item', (object,), dict)
        self.append(item)
