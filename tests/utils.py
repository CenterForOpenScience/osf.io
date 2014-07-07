from nose import SkipTest
from functools import wraps


def requires_module(module):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                __import__(module)
            except ImportError:
                raise SkipTest()
            return fn(*args, **kwargs)
        return wrapper
    return decorator
