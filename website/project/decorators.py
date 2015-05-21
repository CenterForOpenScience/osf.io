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
from framework.mongo.utils import get_or_http_error

from website.models import Node

_load_node_or_fail = lambda pk: get_or_http_error(Node, pk)

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
        raise HTTPError(http.NOT_FOUND)
    return parent, node

def _inject_nodes(kwargs):
    kwargs['parent'], kwargs['node'] = _kwargs_to_nodes(kwargs)

def must_be_valid_project(func):

    # TODO: Check private link

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        _inject_nodes(kwargs)
        return func(*args, **kwargs)

    return wrapped


def must_not_be_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        _inject_nodes(kwargs)
        node = kwargs['node']

        if not node.archiving and node.is_registration:
            raise HTTPError(http.BAD_REQUEST)
        return func(*args, **kwargs)

    return wrapped

def must_be_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        _inject_nodes(kwargs)
        node = kwargs['node']

        if not node.is_registration:
            raise HTTPError(http.BAD_REQUEST)
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
            status.push_status_message("The view-only links you used are expired.")
        raise HTTPError(http.FORBIDDEN)
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


def _must_be_contributor_factory(include_public):
    """Decorator factory for authorization wrappers. Decorators verify whether
    the current user is a contributor on the current project, or optionally
    whether the current project is public.

    :param bool include_public: Check whether current project is public
    :return: Authorization decorator

    """
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            response = None
            _inject_nodes(kwargs)
            node = kwargs['node']

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
            user = kwargs['auth'].user

            key = request.args.get('view_only', '').strip('/')
            #if not login user check if the key is valid or the other privilege

            kwargs['auth'].private_key = key
            if not node.is_public or not include_public:
                if key not in node.private_link_keys_active:
                    if not check_can_access(node=node, user=user, key=key):
                        cas_client = cas.get_client()
                        redirect_url = check_key_expired(key=key, node=node, url=request.url)
                        response = redirect(cas_client.get_login_url(redirect_url))

            return response or func(*args, **kwargs)

        return wrapped

    return wrapper

# Create authorization decorators
must_be_contributor = _must_be_contributor_factory(False)
must_be_contributor_or_public = _must_be_contributor_factory(True)


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
