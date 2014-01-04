import httplib as http

from framework import get_current_user, request, redirect
from framework.exceptions import HTTPError
from framework.auth import get_api_key
from website.project import get_node

###############################################################################
# Decorators
###############################################################################

from decorator import decorator

def must_not_be_registration(fn):
    def wrapped(func, *args, **kwargs):
        if 'project' not in kwargs:
            project = get_node(kwargs['pid'])
            kwargs['project'] = project
        else:
            project = kwargs['project']

        if "nid" in kwargs or "node" in kwargs:
            if 'node' not in kwargs:
                node = get_node(kwargs['nid'])
                kwargs['node'] = node
            else:
                node = kwargs['node']
        else:
            node = None
            kwargs['node'] = node

        if node:
            node_to_use = node
        else:
            node_to_use = project

        if node_to_use.is_registration:
            raise HTTPError(http.NOT_FOUND)

        return fn(*args, **kwargs)
    return decorator(wrapped, fn)

def must_be_valid_project(fn):
    def wrapped(func, *args, **kwargs):
        if 'project' not in kwargs:
            project = get_node(kwargs['pid'])
            kwargs['project'] = project
        else:
            project = kwargs['project']

        if not project or not project.category == 'project':
            raise HTTPError(http.NOT_FOUND)

        if project.is_deleted:
            raise HTTPError(http.GONE)

        if 'nid' in kwargs or 'node' in kwargs:
            if 'node' not in kwargs:
                node = get_node(kwargs['nid'])
                kwargs['node'] = node
            else:
                node = kwargs['node']

            if not node:
                raise HTTPError(http.NOT_FOUND)

            if node.is_deleted:
                raise HTTPError(http.GONE)

        else:
            kwargs['node'] = None

        return fn(*args, **kwargs)
    return decorator(wrapped, fn)

def must_be_contributor(fn):
    def wrapped(func, *args, **kwargs):
        if 'project' not in kwargs:
            project = get_node(kwargs['pid'])
            kwargs['project'] = project
        else:
            project = kwargs['project']

        if "nid" in kwargs or "node" in kwargs:
            if 'node' not in kwargs:
                node = get_node(kwargs['nid'])
                kwargs['node'] = node
            else:
                node = kwargs['node']
        else:
            node = None
            kwargs['node'] = node

        node_to_use = node or project

        if 'user' in kwargs:
            user = kwargs['user']
        else:
            user = get_current_user()
            kwargs['user'] = user

        api_node = kwargs.get('api_node')

        if user is None:
            return redirect('/login/?next={0}'.format(request.path))
        if not node_to_use.is_contributor(user) \
                and api_node != node_to_use:
            raise HTTPError(http.FORBIDDEN)

        return fn(*args, **kwargs)
    return decorator(wrapped, fn)


def must_be_contributor_or_public(fn):
    def wrapped(func, *args, **kwargs):

        if 'project' not in kwargs:
            project = get_node(kwargs['pid'])
            kwargs['project'] = project
        else:
            project = kwargs['project']

        if "nid" in kwargs or "node" in kwargs:
            if 'node' not in kwargs:
                node = get_node(kwargs['nid'])
                kwargs['node'] = node
            else:
                node = kwargs['node']
        else:
            node = None
            kwargs['node'] = node

        node_to_use = node or project

        if 'user' in kwargs:
            user = kwargs['user']
        else:
            user = get_current_user()
            kwargs['user'] = user

        if 'api_node' in kwargs:
            api_node = kwargs['api_node']
        else:
            api_node = get_api_key()
            kwargs['api_node'] = api_node

        if not node_to_use.is_public:
            if user is None:
                return redirect('/login/?next={0}'.format(request.path))
            if not node_to_use.is_contributor(user) \
                    and api_node != node_to_use:
                raise HTTPError(http.FORBIDDEN)

        return fn(*args, **kwargs)
    return decorator(wrapped, fn)

def must_have_addon(addon):
    """Decorator factory that ensures that a given addon is present in the
    `addons_enabled` field of the target node. The decorated function will
    throw a 404 if the required field is not found. Must be applied after a
    decorator that adds `node` and `project` to the target function's keyword
    arguments, such as `must_be_contributor.

    :param str addon: Name of addon
    :return function: Decorator function

    """
    def wrapper(func):
        def wrapped(*args, **kwargs):
            node = kwargs['node'] or kwargs['project']
            if addon not in node.addons_enabled:
                raise HTTPError(http.NOT_FOUND)
            return func(*args, **kwargs)
        return decorator(wrapped, func)
    return wrapper
