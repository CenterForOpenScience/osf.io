import functools

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

from website.addons.dropbox.client import get_client, get_node_client


#TODO (chrisseto) update to getting client from node
def dropbox_decorator(func):

    @must_have_permission('write')
    @must_not_be_registration
    @must_have_addon('dropbox', 'node')
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        with kwargs.get('auth', None) as auth:
            if auth:
                kwargs['dropbox'] = get_client(auth.user)
            else:
                kwargs['dropbox'] = None
        return func(*args, **kwargs)
    return wrapped


def dropbox_decorator_public(func):

    @must_be_contributor_or_public
    @must_have_addon('dropbox', 'node')
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        node = kwargs['node_addon']
        kwargs['dropbox'] = get_node_client(node)
        return func(*args, **kwargs)
    return wrapped
