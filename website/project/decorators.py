# -*- coding: utf-8 -*-

import httplib as http
import functools

from furl import furl
from flask import request

from framework import status
from framework.flask import redirect  # VOL-aware redirect
from framework.exceptions import HTTPError
from framework.auth import Auth, get_current_user, get_api_key
from website.models import Node


def _kwargs_to_nodes(kwargs):
    """Retrieve project and component objects from keyword arguments.

    :param dict kwargs: Dictionary of keyword arguments
    :return: Tuple of project and component

    """
    project = kwargs.get('project') or Node.load(kwargs.get('pid', kwargs.get('nid')))
    if not project:
        raise HTTPError(http.NOT_FOUND)
    if project.category != 'project':
        raise HTTPError(http.BAD_REQUEST)
    if project.is_deleted:
        raise HTTPError(http.GONE)

    if kwargs.get('nid') or kwargs.get('node'):
        node = kwargs.get('node') or Node.load(kwargs.get('nid'))
        if not node:
            raise HTTPError(http.NOT_FOUND)
        if node.is_deleted:
            raise HTTPError(http.GONE)
    else:
        node = None

    return project, node


def must_be_valid_project(func):

    # TODO: Check private link

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
        return func(*args, **kwargs)

    return wrapped


def must_not_be_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
        node = kwargs['node'] or kwargs['project']

        if node.is_registration:
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
    if not node.is_contributor(user) and api_node != node:
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
            kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
            node = kwargs['node'] or kwargs['project']

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
            user = kwargs['auth'].user

            if 'api_node' in kwargs:
                api_node = kwargs['api_node']
            else:
                api_node = get_api_key()
                kwargs['api_node'] = api_node

            key = request.args.get('view_only', '').strip('/')
            #if not login user check if the key is valid or the other privilege

            kwargs['auth'].private_key = key
            if not node.is_public or not include_public:
                if key not in node.private_link_keys_active:
                    if not check_can_access(node=node, user=user,
                            api_node=api_node, key=key):
                        url = '/login/?next={0}'.format(request.path)
                        redirect_url = check_key_expired(key=key, node=node, url=url)
                        response = redirect(redirect_url)

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
        def wrapped(*args, **kwargs):

            if model == 'node':
                kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
                owner = kwargs.get('node') or kwargs.get('project')
            elif model == 'user':
                owner = get_current_user()
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
        def wrapped(*args, **kwargs):

            node_addon = kwargs.get('node_addon')
            if not node_addon:
                kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
                node = kwargs.get('node') or kwargs.get('project')
                node_addon = node.get_addon(addon_name)

            if not node_addon:
                raise HTTPError(http.BAD_REQUEST)

            if not node_addon.user_settings:
                raise HTTPError(http.BAD_REQUEST)

            user = kwargs.get('user') or get_current_user()

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
            kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
            node = kwargs['node'] or kwargs['project']

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
