import functools
import waffle

from flask import request

from framework.auth.core import _get_current_user
from osf import features
from website.ember_osf_web.views import use_ember_app


class MockUser(object):
    is_authenticated = False


def ember_flag_is_active(flag_name):
    """
    Decorator for checking whether ember flag is active.  If so, proxy to ember
    app, otherwise, load old view.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            # Waffle does not enjoy NoneTypes as user values.
            request.user = _get_current_user() or MockUser()

            if waffle.flag_is_active(request, flag_name):
                return use_ember_app()
            else:
                return func(*args, **kwargs)
        return wrapped
    return decorator


def storage_i18n_flag_active():
    request.user = _get_current_user() or MockUser()
    return waffle.flag_is_active(request, features.STORAGE_I18N)
