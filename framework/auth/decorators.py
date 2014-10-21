# -*- coding: utf-8 -*-

import functools

from flask import request

from framework.flask import redirect
from .core import Auth


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
