# -*- coding: utf-8 -*-
import functools
import httplib as http

from furl import furl
from flask import request

from framework import status
from framework.auth import Auth, cas
from framework.flask import redirect  # VOL-aware redirect
from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth
from framework.database import get_or_http_error

from osf.models import AbstractNode
from website import settings, language
from website.util import web_url_for

_load_node_or_fail = lambda pk: get_or_http_error(AbstractNode, pk)


def _kwargs_to_nodes(kwargs):
    """Retrieve project and component objects from keyword arguments.

    :param dict kwargs: Dictionary of keyword arguments
    :return: Tuple of parent and node

    """
    node = kwargs.get('node') or kwargs.get('project')
    parent = kwargs.get('parent')
    if node:
        return parent, node

    pid = kwargs.get('pid')
    nid = kwargs.get('nid')
    if pid and nid:
        node = _load_node_or_fail(nid)
        parent = _load_node_or_fail(pid)
    elif pid and not nid:
        node = _load_node_or_fail(pid)
    elif nid and not pid:
        node = _load_node_or_fail(nid)
    elif not pid and not nid:
        raise HTTPError(
            http.NOT_FOUND,
            data={
                'message_short': 'Node not found',
                'message_long': 'No Node with that primary key could be found',
            }
        )
    return parent, node


def _inject_nodes(kwargs):
    kwargs['parent'], kwargs['node'] = _kwargs_to_nodes(kwargs)


def must_not_be_rejected(func):
    """Ensures approval/disapproval requests can't reach Sanctions that have
    already been rejected.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        node = get_or_http_error(AbstractNode, kwargs.get('nid', kwargs.get('pid')), allow_deleted=True)
        if node.sanction and node.sanction.is_rejected:
            raise HTTPError(http.GONE, data=dict(
                message_long='This registration has been rejected'
            ))

        return func(*args, **kwargs)

    return wrapped

def must_be_valid_project(func=None, retractions_valid=False, quickfiles_valid=False):
    """ Ensures permissions to retractions are never implicitly granted. """

    # TODO: Check private link
    def must_be_valid_project_inner(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            _inject_nodes(kwargs)

            if getattr(kwargs['node'], 'is_collection', True) or (getattr(kwargs['node'], 'is_quickfiles', True) and not quickfiles_valid):
                raise HTTPError(
                    http.NOT_FOUND
                )

            if not retractions_valid and getattr(kwargs['node'].retraction, 'is_retracted', False):
                raise HTTPError(
                    http.BAD_REQUEST,
                    data=dict(message_long='Viewing withdrawn registrations is not permitted')
                )
            else:
                return func(*args, **kwargs)

        return wrapped

    if func:
        return must_be_valid_project_inner(func)

    return must_be_valid_project_inner


def must_be_public_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        _inject_nodes(kwargs)

        node = kwargs['node']

        if not node.is_public or not node.is_registration:
            raise HTTPError(
                http.BAD_REQUEST,
                data=dict(message_long='Must be a public registration to view')
            )

        return func(*args, **kwargs)

    return wrapped


def must_not_be_retracted_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        _inject_nodes(kwargs)

        node = kwargs['node']

        if node.is_retracted:
            return redirect(
                web_url_for('resolve_guid', guid=node._id)
            )
        return func(*args, **kwargs)

    return wrapped


def must_not_be_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        _inject_nodes(kwargs)
        node = kwargs['node']

        if node.is_registration and not node.archiving:
            raise HTTPError(
                http.BAD_REQUEST,
                data={
                    'message_short': 'Registrations cannot be changed',
                    'message_long': "The operation you're trying to do cannot be applied to registered projects, which are not allowed to be changed",
                }
            )
        return func(*args, **kwargs)

    return wrapped

def must_be_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        _inject_nodes(kwargs)
        node = kwargs['node']

        if not node.is_registration:
            raise HTTPError(
                http.BAD_REQUEST,
                data={
                    'message_short': 'Registered Nodes only',
                    'message_long': 'This view is restricted to registered Nodes only',
                }
            )
        return func(*args, **kwargs)

    return wrapped


def check_can_access(node, user, key=None, api_node=None):
    """View helper that returns whether a given user can access a node.
    If ``user`` is None, returns False.

    :rtype: boolean
    :raises: HTTPError (403) if user cannot access the node
    """
    if user is None:
        return False
    if not node.can_view(Auth(user=user)) and api_node != node:
        if key in node.private_link_keys_deleted:
            status.push_status_message('The view-only links you used are expired.', trust=False)
        raise HTTPError(
            http.FORBIDDEN,
            data={'message_long': ('User has restricted access to this page. If this should not '
                                   'have occurred and the issue persists, ' + language.SUPPORT_LINK)}
        )
    return True


def check_key_expired(key, node, url):
    """check if key expired if is return url with args so it will push status message
        else return url
        :param str key: the private link key passed in
        :param Node node: the node object wants to access
        :param str url: the url redirect to
        :return: url with pushed message added if key expired else just url
    """
    if key in node.private_link_keys_deleted:
        url = furl(url).add({'status': 'expired'}).url

    return url


def _must_be_contributor_factory(include_public, include_view_only_anon=True):
    """Decorator factory for authorization wrappers. Decorators verify whether
    the current user is a contributor on the current project, or optionally
    whether the current project is public.

    :param bool include_public: Check whether current project is public
    :param bool include_view_only_anon: Checks view_only anonymized links
    :return: Authorization decorator

    """
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            _inject_nodes(kwargs)

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)

            response = check_contributor_auth(kwargs['node'], kwargs['auth'], include_public, include_view_only_anon)

            return response or func(*args, **kwargs)

        return wrapped

    return wrapper

# Create authorization decorators
must_be_contributor = _must_be_contributor_factory(False)
must_be_contributor_or_public = _must_be_contributor_factory(True)
must_be_contributor_or_public_but_not_anonymized = _must_be_contributor_factory(include_public=True, include_view_only_anon=False)


def must_have_addon(addon_name, model):
    """Decorator factory that ensures that a given addon has been added to
    the target node. The decorated function will throw a 404 if the required
    addon is not found. Must be applied after a decorator that adds `node` and
    `project` to the target function's keyword arguments, such as
    `must_be_contributor.

    :param str addon_name: Name of addon
    :param str model: Name of model
    :returns: Decorator function

    """
    def wrapper(func):

        @functools.wraps(func)
        @collect_auth
        def wrapped(*args, **kwargs):
            if model == 'node':
                _inject_nodes(kwargs)
                owner = kwargs['node']
            elif model == 'user':
                auth = kwargs.get('auth')
                owner = auth.user if auth else None
                if owner is None:
                    raise HTTPError(http.UNAUTHORIZED)
            else:
                raise HTTPError(http.BAD_REQUEST)

            addon = owner.get_addon(addon_name)
            if addon is None:
                raise HTTPError(http.BAD_REQUEST)

            kwargs['{0}_addon'.format(model)] = addon

            return func(*args, **kwargs)

        return wrapped

    return wrapper


def must_be_addon_authorizer(addon_name):
    """

    :param str addon_name: Name of addon
    :returns: Decorator function

    """
    def wrapper(func):

        @functools.wraps(func)
        @collect_auth
        def wrapped(*args, **kwargs):

            node_addon = kwargs.get('node_addon')
            if not node_addon:
                _inject_nodes(kwargs)
                node = kwargs['node']
                node_addon = node.get_addon(addon_name)

            if not node_addon:
                raise HTTPError(http.BAD_REQUEST)

            if not node_addon.user_settings:
                raise HTTPError(http.BAD_REQUEST)

            auth = kwargs.get('auth')
            user = kwargs.get('user') or (auth.user if auth else None)

            if node_addon.user_settings.owner != user:
                raise HTTPError(http.FORBIDDEN)

            return func(*args, **kwargs)

        return wrapped

    return wrapper


def must_have_permission(permission):
    """Decorator factory for checking permissions. Checks that user is logged
    in and has necessary permissions for node. Node must be passed in keyword
    arguments to view function.

    :param list permissions: List of accepted permissions
    :returns: Decorator function for checking permissions
    :raises: HTTPError(http.UNAUTHORIZED) if not logged in
    :raises: HTTPError(http.FORBIDDEN) if missing permissions

    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            # Ensure `project` and `node` kwargs
            _inject_nodes(kwargs)
            node = kwargs['node']

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
            user = kwargs['auth'].user

            # User must be logged in
            if user is None:
                raise HTTPError(http.UNAUTHORIZED)

            # User must have permissions
            if not node.has_permission(user, permission):
                raise HTTPError(http.FORBIDDEN)

            # Call view function
            return func(*args, **kwargs)

        # Return decorated function
        return wrapped

    # Return decorator
    return wrapper

def must_have_write_permission_or_public_wiki(func):
    """ Checks if user has write permission or wiki is public and publicly editable. """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        # Ensure `project` and `node` kwargs
        _inject_nodes(kwargs)

        wiki = kwargs['node'].get_addon('wiki')

        if wiki and wiki.is_publicly_editable:
            return func(*args, **kwargs)
        else:
            return must_have_permission('write')(func)(*args, **kwargs)

    # Return decorated function
    return wrapped

def http_error_if_disk_saving_mode(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _inject_nodes(kwargs)
        node = kwargs['node']

        if settings.DISK_SAVING_MODE:
            raise HTTPError(
                http.METHOD_NOT_ALLOWED,
                redirect_url=node.url
            )
        return func(*args, **kwargs)
    return wrapper

def check_contributor_auth(node, auth, include_public, include_view_only_anon):
    response = None

    user = auth.user

    auth.private_key = request.args.get('view_only', '').strip('/')

    if not include_view_only_anon:
        from osf.models import PrivateLink
        try:
            link_anon = PrivateLink.objects.filter(key=auth.private_key).values_list('anonymous', flat=True).get()
        except PrivateLink.DoesNotExist:
            link_anon = None

    if not node.is_public or not include_public:
        if not include_view_only_anon and link_anon:
            if not check_can_access(node=node, user=user):
                raise HTTPError(http.UNAUTHORIZED)
        elif auth.private_key not in node.private_link_keys_active:
            if not check_can_access(node=node, user=user, key=auth.private_key):
                redirect_url = check_key_expired(key=auth.private_key, node=node, url=request.url)
                if request.headers.get('Content-Type') == 'application/json':
                    raise HTTPError(http.UNAUTHORIZED)
                else:
                    response = redirect(cas.get_login_url(redirect_url))

    return response
