import httplib as http
import functools
import logging

from furl import furl
from framework import request, redirect, status
from framework.exceptions import HTTPError
from framework.auth import get_current_user, get_api_key
from framework.auth.decorators import Auth
from framework.sessions import add_key_to_url
from website.models import Node

logger = logging.getLogger(__name__)

debug = logger.debug


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


def check_can_access(node, user, api_node=None, has_deleted_keys=False):
    """View helper that returns whether a given user can access a node.
    If ``user`` is None, returns False.

    :rtype: boolean
    :raises: HTTPError (403) if user cannot access the node
    """
    if user is None:
        return False
    if not node.is_contributor(user) \
            and api_node != node:
        if has_deleted_keys:
            status.push_status_message("The private links you used are expired.")
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


def has_deleted_keys(key_ring, node, user):
    """check if there is deleted keys, if there is delete it from user.private_links
        :param set key_ring: the set of kings user have
        :param Node node: the node object wants to access
        :param User user: the user who requires to access the node
        :return: True if there are expired keys to delete and delete the key else return False
    """
    deleted_keys = key_ring.intersection(node.private_link_keys_deleted)

    for link in deleted_keys:
        for x in user.private_links:
            if x.key == link:
                user.private_links.remove(x)
                break

    if deleted_keys:
        user.save()
        return True

    return False


def choose_key(key, key_ring, node, auth, api_node=None):
    """Returns ``None`` if the given key is valid, else return a redirect
    response to the requested URL with the correct key from the key_ring.
    """
    if key in node.private_link_keys_active:
        auth.private_key = key
        return

    auth.private_key = key_ring.intersection(
        node.private_link_keys_active
    ).pop()
    #do a redirect to reappend the key to url only if the user
    # isn't a contributor
    if auth.user is None or (not node.is_contributor(auth.user) and api_node != node):
        new_url = add_key_to_url(request.path, auth.private_key)
        return redirect(new_url)



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

            key = request.args.get('key', '').strip('/')
            #if not login user check if the key is valid or the other privilege
            if not kwargs['auth'].user:
                kwargs['auth'].private_key = key
                if not node.is_public or not include_public:
                    if key not in node.private_link_keys_active:
                        if not check_can_access(node=node, user=user,
                                api_node=api_node):
                            url = '/login/?next={0}'.format(request.path)
                            redirect_url = check_key_expired(key=key, node=node, url = url)
                            response = redirect(redirect_url)

            #for login user
            else:
                #key first time show up record it in the key ring
                if key not in kwargs['auth'].user.private_link_keys:
                    for node_link in node.private_links_active:
                        if node_link.key == key:
                            user.private_links.append(node_link)
                            kwargs['auth'].user.save()
                            break

                key_ring = set(kwargs['auth'].user.private_link_keys)

                #check if the keyring has intersection with node's private link
                # if no intersction check other privilege
                if not node.is_public or not include_public:
                    if key_ring.isdisjoint(node.private_link_keys_active):
                        delete_key_check = has_deleted_keys(
                            key_ring=key_ring, node=node, user=kwargs['auth'].user)

                        if not check_can_access(node=node, user=user, has_deleted_keys=delete_key_check,
                                api_node=api_node):
                            url = '/login/?next={0}'.format(request.path)
                            redirect_url = check_key_expired(key=key, node=node, url = url)
                            response = redirect(redirect_url)

                        kwargs['auth'].private_key = None

                    #has intersection: check if the link is valid if not use other key
                    # in the key ring
                    else:
                        response = choose_key(
                            key=key, key_ring=key_ring, node=node,
                            auth=kwargs['auth'], api_node=api_node)
                else:
                    kwargs['auth'].private_key = None
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
    :return function: Decorator function

    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            if model == 'node':
                owner = kwargs['node'] or kwargs['project']
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
