import waffle
from rest_framework.exceptions import NotFound

def waffle_feature_is_active(request, instance_type, instance_name):
    """
    Determine if flag, switch, or sample is active for the given user.

    :param request: Django request
    :param instance_type: Either "flag", "switch", or "sample"
    :param instance_name: *Name* of the flag/switch/sample
    :return: Boolean. Is the flag/switch/or sample active?
    """
    waffle_map = {
        'flag': {
            'waffle_func': waffle.flag_is_active,
            'waffle_args': (request, instance_name),
        },
        'switch': {
            'waffle_func': waffle.switch_is_active,
            'waffle_args': (instance_name,),
        },
        'sample': {
            'waffle_func': waffle.sample_is_active,
            'waffle_args': (instance_name,),
        },
    }[instance_type]
    return waffle_map['waffle_func'](*waffle_map['waffle_args'])

def require_flag(flag_name):
    """
    Decorator to check whether waffle flag is active. If inactive, raises NotFound.
    """
    def wrapper(fn):
        return check_waffle_object(fn, 'flag', flag_name)
    return wrapper

def require_switch(switch_name):
    """
    Decorator to check whether waffle switch is active. If inactive, raises NotFound.
    """
    def wrapper(fn):
        return check_waffle_object(fn, 'switch', switch_name)
    return wrapper

def require_sample(sample_name):
    """
    Decorator to check whether waffle sample is active. If inactive, raises NotFound.
    """
    def wrapper(fn):
        return check_waffle_object(fn, 'sample', sample_name)
    return wrapper

def check_waffle_object(fn, instance_type, instance_name):
    def check_waffle_object(*args, **kwargs):
        if waffle_feature_is_active(args[0].request, instance_type, instance_name):
            return fn(*args, **kwargs)
        else:
            raise NotFound('Endpoint is disabled.')
    return check_waffle_object
