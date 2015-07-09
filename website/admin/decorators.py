from flask import request
import functools
import httplib as http

from framework.exceptions import HTTPError
from framework.auth import Auth

from website.admin.model import Role

def must_be_super_on(group):
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
            user_role = Role.for_user(kwargs['auth'].user, group=group)
            if not user_role or not user_role.is_super:
                raise HTTPError(http.UNAUTHORIZED)
            return func(*args, **kwargs)

        return wrapped
    return wrapper
