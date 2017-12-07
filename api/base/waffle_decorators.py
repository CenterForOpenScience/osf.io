import waffle
from rest_framework.exceptions import NotFound

def require_flag(flag_name):
    """
    Decorator to check whether flag is active.

    If inactive, raise NotFound.
    """
    def wrapper(fn):
        def check_flag(*args,**kwargs):
            if waffle.flag_is_active(args[0].request, flag_name):
                return fn(*args,**kwargs)
            else:
                raise NotFound('Endpoint is disabled.')
        return check_flag
    return wrapper
