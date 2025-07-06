import functools

from flask import request

from api.waffle.utils import flag_is_active
from website.external_web_app.views import use_primary_web_app


def ember_flag_is_active(flag_name):
    """
    Decorator for checking whether ember flag is active.  If so, proxy to ember
    app, otherwise, load old view.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if flag_is_active(request, flag_name):
                return use_primary_web_app()
            else:
                return func(*args, **kwargs)
        return wrapped
    return decorator
