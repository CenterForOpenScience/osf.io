import functools
import httplib

from framework.exceptions import HTTPError, PermissionsError

from admin.rdm_addons.utils import validate_rdm_addons_allowed


def must_be_rdm_addons_allowed(addon_short_name=None):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if 'auth' not in kwargs:
                raise HTTPError(httplib.UNAUTHORIZED)

            auth = kwargs['auth']

            try:
                validate_rdm_addons_allowed(auth, addon_short_name)
            except PermissionsError as e:
                return {'message_long': e.message}, httplib.FORBIDDEN

            return func(*args, **kwargs)

        return wrapped

    return wrapper
