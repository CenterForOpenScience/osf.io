import functools
from framework.flask import request, redirect
from . import get_current_user, get_api_key, get_current_node


# TODO: This belongs in auth.__init__ or auth.model
class Auth(object):

    def __init__(self, user=None, api_key=None, api_node=None,
                 private_key=None):
        self.user = user
        self.api_key = api_key
        self.api_node = api_node
        self.private_key = private_key

    @property
    def logged_in(self):
        return self.user is not None

    @classmethod
    def from_kwargs(cls, request_args, kwargs):
        user = request_args.get('user') or kwargs.get('user') or get_current_user()
        api_key = request_args.get('api_key') or kwargs.get('api_key') or get_api_key()
        api_node = request_args.get('api_node') or kwargs.get('api_node') or get_current_node()
        private_key = request_args.get('view_only')
        return cls(
            user=user,
            api_key=api_key,
            api_node=api_node,
            private_key=private_key,
        )

#### Auth-related decorators ##################################################

def collect_auth(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
        return func(*args, **kwargs)

    return wrapped

def must_be_logged_in(func):
    """Require that user be logged in. Modifies kwargs to include the current
    user.

    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
        if kwargs['auth'].logged_in:
            return func(*args, **kwargs)
        else:
            return redirect('/login/?next={0}'.format(request.path))

    return wrapped
