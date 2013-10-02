from framework import get_current_user, push_status_message, redirect
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
            push_status_message('Registrations are read-only')
            return redirect(node_to_use.url())

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
            push_status_message('Not a valid project')
            return redirect('/')

        if project.is_deleted:
            push_status_message('This project has been deleted')
            return redirect('')

        if "nid" in kwargs or "node" in kwargs:
            if 'node' not in kwargs:
                node = get_node(kwargs['nid'])
                kwargs['node'] = node
            else:
                node = kwargs['node']

            if not node:
                push_status_message('Not a valid component')
                return redirect('/')

            if node.is_deleted:
                push_status_message('This component has been deleted')
                return redirect('/')
            
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

        if not node_to_use.is_contributor(user) \
                and api_node != node_to_use:
            push_status_message('You are not authorized to perform that action \
                for this node')
            return redirect('/')
        
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

        if not node_to_use.is_public \
                and not node_to_use.is_contributor(user) \
                and api_node != node_to_use:
            push_status_message('You are not authorized to perform that action \
                for this node')
            return redirect('/')
        
        return fn(*args, **kwargs)
    return decorator(wrapped, fn)