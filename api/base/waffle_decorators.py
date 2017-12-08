import waffle
from rest_framework.exceptions import NotFound

def require_flag(flag_name):
    """
    Decorator to check whether waffle flag is active.

    If inactive, raise NotFound.
    """
    def wrapper(fn):
        def check_flag(*args, **kwargs):
            if waffle.flag_is_active(args[0].request, flag_name):
                return fn(*args, **kwargs)
            else:
                raise NotFound('Endpoint is disabled.')
        return check_flag
    return wrapper

def require_switch(switch_name):
    """
    Decorator to check whether waffle switch is active.

    If inactive, raise NotFound.
    """
    def wrapper(fn):
        def check_switch(*args, **kwargs):
            if waffle.switch_is_active(switch_name):
                return fn(*args, **kwargs)
            else:
                raise NotFound('Endpoint is disabled.')
        return check_switch
    return wrapper

def require_sample(sample_name):
    """
    Decorator to check whether waffle sample is active.

    If inactive, raise NotFound.
    """
    def wrapper(fn):
        def check_sample(*args, **kwargs):
            if waffle.sample_is_active(sample_name):
                return fn(*args, **kwargs)
            else:
                raise NotFound('Endpoint is disabled.')
        return check_sample
    return wrapper
